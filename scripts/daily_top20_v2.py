"""Daily close-leader research engine. Offline, no broker or Sheet side effects.
JSON snapshot -> immutable prediction; prediction + completed close snapshot -> review.
Source completeness is externally attested, never proved by this validator.
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import pathlib
import unittest
from zoneinfo import ZoneInfo

VERSION = "DAILY-TOP20-V2.0"
METHOD = "PREMARKET_GAP_V0_UNVALIDATED"
ET = ZoneInfo("America/New_York")
COMMON = {"CS", "ORDINARY"}
EXCHANGES = {"NYSE", "NASDAQ", "AMEX"}
def stamp(s):
    x = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    if x.tzinfo is None:
        raise ValueError("timestamp requires timezone")
    return x
def numeric(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)
def digest(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
def unique(rows):
    keys = [r["security_id"] for r in rows]
    tickers = [r["ticker"] for r in rows]
    if len(set(keys)) != len(keys) or len(set(tickers)) != len(tickers):
        raise ValueError("duplicate security_id or ticker")
def rank(rows, key):
    return [r["security_id"] for r in sorted(
        (r for r in rows if numeric(r.get(key))),
        key=lambda r: (-r[key], r["ticker"], r["security_id"]))]
def predict(s):
    cutoff, close = stamp(s["cutoff_utc"]), stamp(s["regular_close_utc"])
    if cutoff >= close or close.astimezone(ET).date().isoformat() != s["date_et"]:
        raise ValueError("invalid session cutoff")
    if stamp(s["snapshot_known_at_utc"]) > cutoff:
        raise ValueError("future snapshot")
    prior_session = dt.date.fromisoformat(s["previous_session_et"])
    if prior_session >= dt.date.fromisoformat(s["date_et"]):
        raise ValueError("invalid previous regular session")
    rows = s["rows"]
    unique(rows)
    eligible, rejected, unknown = [], [], []
    for row in rows:
        r = dict(row)
        sid = r["security_id"]
        if r.get("known_at_utc") and stamp(r["known_at_utc"]) > cutoff:
            raise ValueError("future candidate evidence")
        if r.get("history_end_et") and dt.date.fromisoformat(r["history_end_et"]) >= dt.date.fromisoformat(s["date_et"]):
            raise ValueError("same-day/future history")
        if not r.get("known_at_utc"):
            unknown.append((sid, "KNOWN_AT_UNKNOWN"))
            continue
        if r.get("type") in (None, "", "UNKNOWN") or r.get("exchange") in (None, "", "UNKNOWN"):
            unknown.append((sid, "TYPE_OR_EXCHANGE_UNKNOWN"))
            continue
        if r["type"] not in COMMON or r["exchange"] not in EXCHANGES or r.get("spac") is True:
            rejected.append((sid, "SECURITY_TYPE"))
            continue
        if r.get("history_end_et") != s["previous_session_et"]:
            unknown.append((sid, "MISSING_OR_STALE_PRIOR_SESSION"))
            continue
        vals = [r.get(k) for k in ("prior_close", "adv20", "listed_sessions", "last_price")]
        if r.get("spac") is not False or not all(map(numeric, vals)) or r.get("ca_verified") is not True:
            unknown.append((sid, "ELIGIBILITY_OR_CA_UNKNOWN"))
            continue
        p, adv, age_days, last = vals
        if min(p, last) <= 0 or adv < 0 or age_days < 0 or int(age_days) != age_days:
            raise ValueError("invalid numeric data")
        if not r.get("trade_at_utc"):
            unknown.append((sid, "NO_TRADE_TIMESTAMP"))
            continue
        age = (cutoff - stamp(r["trade_at_utc"])).total_seconds()
        if age < 0 or stamp(r["trade_at_utc"]) > stamp(r["known_at_utc"]):
            raise ValueError("future trade or trade after known_at")
        if age > 180:
            unknown.append((sid, "STALE_TRADE"))
            continue
        if last < 3 or adv < 10_000_000 or age_days < 20:
            rejected.append((sid, "NUMERIC_ELIGIBILITY"))
            continue
        r["gap"] = last / p - 1
        r["age_seconds"] = age
        eligible.append(r)
    order = rank(eligible, "gap")
    if len(order) < 20:
        raise ValueError("fewer than 20 defensible eligible scored securities")
    shadow = {k: rank(eligible, k)[:20] if all(numeric(r.get(k)) for r in eligible) else None
              for k in ("rms5", "prev1", "rev3")}
    quality = "EVIDENCE_READY_EXTERNAL_VERIFICATION_REQUIRED" if (
        s.get("full_roster_verified") is True and not unknown
        and s.get("source_verified") is True
        and s.get("expected_universe_n") == len(rows)
    ) else "PROVISIONAL_NOT_CLEAN"
    packet = dict(version=VERSION, method=METHOD, run_id=s["run_id"], date_et=s["date_et"],
                  cutoff_utc=s["cutoff_utc"], regular_close_utc=s["regular_close_utc"],
                  input_hash=digest(s), roster_n=len(rows), eligible_n=len(eligible),
                  rejected=rejected, unknown=unknown, quality=quality,
                  universe=[{"security_id":r["security_id"],"ticker":r["ticker"],
                             "prior_close":r["prior_close"],"last_price":r["last_price"],
                             "gap":r["gap"]} for r in eligible],
                  full_rank=order, top20=order[:20], top5=order[:5], shadows=shadow)
    return {"packet":packet, "sha256":digest(packet)}
def review(f, o):
    p = f["packet"]
    if digest(p) != f["sha256"]:
        raise ValueError("prediction hash mismatch")
    if p["run_id"] != o["run_id"] or p["date_et"] != o["date_et"]:
        raise ValueError("review cohort mismatch")
    if stamp(o["observed_at_utc"]) < stamp(p["regular_close_utc"]):
        raise ValueError("session not completed")
    if (len(p["top20"]) != 20 or len(set(p["full_rank"])) != len(p["full_rank"])
        or p["top20"] != p["full_rank"][:20] or p["top5"] != p["top20"][:5]):
        raise ValueError("rank/selection mismatch")
    unique(o["rows"])
    lookup = {r["security_id"]:r for r in o["rows"]}
    expected = {r["security_id"] for r in p["universe"]}
    if set(p["full_rank"]) != expected or set(lookup) != expected:
        raise ValueError("incomplete or different review universe")
    actual = []
    for r in p["universe"]:
        a = lookup[r["security_id"]]
        if (a["ticker"] != r["ticker"] or a.get("same_share_basis") is not True or
            a.get("session_date_et") != p["date_et"] or not a.get("source") or
            not numeric(a.get("close")) or a["close"] <= 0):
            raise ValueError("unverified close, identity or corporate action")
        actual.append(dict(security_id=r["security_id"], ticker=r["ticker"],
                           close_return=a["close"]/r["prior_close"]-1,
                           post_cutoff_return=a["close"]/r["last_price"]-1))
    order = rank(actual,"close_return")
    winners=set(order[:20])
    def overlap(a,b): return len(set(a)&set(b))
    result = dict(run_id=p["run_id"], prediction_sha256=f["sha256"], actual_top20=order[:20],
                  actual_top5=order[:5], overlap20=overlap(p["top20"],winners),
                  top5_in_actual20=overlap(p["top5"],winners),
                  exact_top5_overlap=overlap(p["top5"],order[:5]),
                  shadow_overlap20={k:overlap(v,winners) if v is not None and len(v)==20 else None for k,v in p["shadows"].items()},
                  actual=actual, quality=p["quality"], coverage_scope="SAME_SCORED_COHORT_ONLY_PENDING_EXTERNAL_MARKET_QA",
                  market_recall=None)
    return result
def write_once(path, value):
    with pathlib.Path(path).open("x", encoding="utf-8") as f:
        json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False)
def fixture():
    return dict(run_id="TEST",date_et="2026-11-24",previous_session_et="2026-11-23",cutoff_utc="2026-11-24T14:25:00Z",
                regular_close_utc="2026-11-24T21:00:00Z",snapshot_known_at_utc="2026-11-24T14:25:00Z",
                expected_universe_n=25,full_roster_verified=True,source_verified=True,
                rows=[dict(security_id=str(i),ticker=f"T{i:02}",type="CS",exchange="NYSE",spac=False,
                           prior_close=10,adv20=20_000_000,listed_sessions=50,last_price=10+i/10,
                           trade_at_utc="2026-11-24T14:24:30Z",known_at_utc="2026-11-24T14:24:45Z",
                           history_end_et="2026-11-23",ca_verified=True,rms5=i,prev1=-i,rev3=i)
                      for i in range(25)])
class Tests(unittest.TestCase):
    def test_rank(self):
        f=predict(fixture()); self.assertEqual(f["packet"]["top20"][0],"24"); self.assertEqual(len(f["packet"]["top5"]),5)
    def test_future_trade(self):
        s=fixture(); s["rows"][0]["trade_at_utc"]="2026-11-24T14:26:00Z"
        with self.assertRaises(ValueError): predict(s)
    def test_same_day_history(self):
        s=fixture(); s["rows"][0]["history_end_et"]="2026-11-24"
        with self.assertRaises(ValueError): predict(s)
    def test_stale(self):
        s=fixture(); s["rows"][0]["trade_at_utc"]="2026-11-24T14:20:00Z"
        self.assertEqual(predict(s)["packet"]["quality"],"PROVISIONAL_NOT_CLEAN")
    def test_duplicate(self):
        s=fixture(); s["rows"].append(s["rows"][0])
        with self.assertRaises(ValueError): predict(s)
    def test_ineligible(self):
        s=fixture(); s["rows"][-1]["type"]="ETF"
        self.assertNotIn("24",predict(s)["packet"]["top20"])
    def test_too_few(self):
        s=fixture(); s["rows"]=s["rows"][:19]
        with self.assertRaises(ValueError): predict(s)
    def test_review_and_hash(self):
        f=predict(fixture()); p=f["packet"]; o=dict(run_id="TEST",date_et=p["date_et"],observed_at_utc=p["regular_close_utc"],rows=[dict(security_id=r["security_id"],ticker=r["ticker"],close=r["last_price"],same_share_basis=True,session_date_et=p["date_et"],source="SYNTHETIC") for r in p["universe"]])
        self.assertEqual(review(f,o)["overlap20"],20)
        o["rows"].pop()
        with self.assertRaises(ValueError): review(f,o)
        f["packet"]["top20"][0]="tamper"
        with self.assertRaises(ValueError): review(f,o)
    def test_stale_history(self):
        s=fixture(); s["rows"][0]["history_end_et"]="2026-11-20"
        self.assertIn(("0","MISSING_OR_STALE_PRIOR_SESSION"),predict(s)["packet"]["unknown"])
    def test_missing_shadow(self):
        s=fixture(); s["rows"][0]["rms5"]=None
        self.assertIsNone(predict(s)["packet"]["shadows"]["rms5"])
    def test_unknown_type(self):
        s=fixture(); s["rows"][0]["type"]="UNKNOWN"
        self.assertIn(("0","TYPE_OR_EXCHANGE_UNKNOWN"),predict(s)["packet"]["unknown"])
    def test_missing_history(self):
        s=fixture(); del s["rows"][0]["history_end_et"]
        self.assertIn(("0","MISSING_OR_STALE_PRIOR_SESSION"),predict(s)["packet"]["unknown"])
    def test_unfinished(self):
        f=predict(fixture())
        with self.assertRaises(ValueError): review(f,dict(run_id="TEST",date_et="2026-11-24",observed_at_utc="2026-11-24T20:59:00Z",rows=[]))
if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("mode",choices=["predict","review","self-test"]);p.add_argument("--snapshot");p.add_argument("--frozen");p.add_argument("--output")
    a=p.parse_args()
    if a.mode=="self-test": unittest.main(argv=[__file__])
    else:
        with open(a.snapshot,encoding="utf-8") as f: s=json.load(f)
        if a.mode=="predict": v=predict(s)
        else:
            with open(a.frozen,encoding="utf-8") as f: v=review(json.load(f),s)
        write_once(a.output,v)
