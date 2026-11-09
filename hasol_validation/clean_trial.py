"""HASOL experimental A/B/C trial. No production Frozen or broker actions.

The lock command has no market/model input. The second stage rejects any missing
or modified blind lock and uses ONE eligible set, cutoff and baseline for A/B/C.
This does not control what an external AI/web search saw before invoking lock.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

VERSION = "HASOL-CLEAN-TRIAL-0.1"
UTC = timezone.utc
FORBIDDEN = re.compile(
    r"\b(?:stock|share)\s+price\b|\bpremarket\b|\bafter.hours\b|"
    r"\b(?:stock|shares)\s+(?:jumped|rose|fell|dropped|rallied|sold\s+off)\b|"
    r"\b(?:price|trading)\s+(?:reaction|volume)\b|\bmarket\s+cap\b|"
    r"주가|주식가격|거래량|장전\s*급등|주가\s*반응|갭상승|갭하락",
    re.IGNORECASE,
)
ISSUER_FIELDS = {
    "ticker", "security_id", "known_at_utc", "source_url", "fact",
    "novelty", "expectation_delta", "fundamental_impact",
}
MARKET_FIELDS = {
    "ticker", "security_id", "last_price", "observed_at_utc", "adtv20_usd",
    "listing_sessions", "security_type", "exchange", "is_spac",
    "momentum5_pct", "relative_volume20", "atr20_pct", "source",
}


class TrialError(ValueError):
    """An experiment cannot safely advance to the next stage."""


def _date(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise TrialError(f"invalid timestamp: {value!r}") from exc
    if result.tzinfo is None:
        raise TrialError("timestamps require timezone offset")
    return result.astimezone(UTC)


def _read(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TrialError(f"JSON object expected: {path}")
    return data


def _dump(data: object) -> bytes:
    return (json.dumps(data, sort_keys=True, ensure_ascii=False, indent=2)
            + "\n").encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _exclusive(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Never silently replace a lock, ranking, or retrospective.
    with path.open("xb") as file:
        file.write(_dump(data))


def _keys(row: dict, expected: set[str], where: str) -> None:
    if not isinstance(row, dict) or set(row) != expected:
        raise TrialError(f"{where}: missing or unexpected fields")


def _ticker(row: dict) -> str:
    symbol = row["ticker"]
    if not isinstance(symbol, str) or not re.fullmatch(r"[A-Z][A-Z0-9.]{0,9}", symbol):
        raise TrialError(f"invalid ticker {symbol!r}")
    return symbol


def _number(value: object, name: str, *, low: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise TrialError(f"{name} must be finite numeric")
    val = float(value)
    if low is not None and val < low:
        raise TrialError(f"{name} below {low}")
    return val


def _canonical_set(rows: list[dict], label: str) -> set[str]:
    if not isinstance(rows, list):
        raise TrialError(f"{label} must be an array")
    names = [_ticker(row) for row in rows]
    if len(names) != len(set(names)):
        raise TrialError(f"{label} duplicate ticker")
    return set(names)


def lock_issuer(issuer_path: Path, output_dir: Path) -> dict:
    """Stage 1: accepts ONLY issuer-only information, never a market file."""
    if (output_dir / "blind.json").exists() or (output_dir / "blind_manifest.json").exists():
        raise TrialError("blind lock already exists; never overwrite")
    raw = _read(issuer_path)
    _keys(raw, {"run_id", "cutoff_utc", "candidates"}, "issuer")
    cutoff = _date(raw["cutoff_utc"])
    now = datetime.now(UTC)
    if cutoff <= now:
        raise TrialError("cutoff has passed: this cannot be a new prospective blind lock")
    candidates = raw["candidates"]
    names = _canonical_set(candidates, "issuer")
    if len(names) < 20:
        raise TrialError("trial requires at least 20 pre-registered candidates")
    for row in candidates:
        _keys(row, ISSUER_FIELDS, f"issuer {row.get('ticker')}")
        if not isinstance(row["security_id"], str) or not row["security_id"].strip():
            raise TrialError("security_id required")
        if not isinstance(row["source_url"], str) or not row["source_url"].startswith("https://"):
            raise TrialError("issuer source must be https URL")
        if not isinstance(row["fact"], str) or len(row["fact"].strip()) < 15:
            raise TrialError("substantial issuer fact and source required")
        if FORBIDDEN.search(row["fact"]) or FORBIDDEN.search(row["source_url"]):
            raise TrialError(f"{row['ticker']}: price/reaction text entered blind packet")
        if _date(row["known_at_utc"]) > now:
            raise TrialError("issuer fact was not yet known at lock time")
        for key, low, high in [("novelty", 0, 3), ("expectation_delta", -3, 3),
                               ("fundamental_impact", 0, 3)]:
            value = row[key]
            if type(value) is not int or not low <= value <= high:
                raise TrialError(f"{row['ticker']}: invalid {key}")
    packet = {
        "version": VERSION, "run_id": raw["run_id"], "cutoff_utc": raw["cutoff_utc"],
        "candidates": sorted(candidates, key=lambda x: x["ticker"]),
    }
    blob = _dump(packet)
    manifest = {
        "run_id": raw["run_id"], "cutoff_utc": raw["cutoff_utc"],
        "locked_at_utc": now.isoformat(), "blind_sha256": _sha(blob),
        "candidate_n": len(names), "stage": "BLIND_LOCKED",
        "external_web_or_model_price_exposure": "NOT_ATTESTED",
        "clean_forward_credit": False,
    }
    _exclusive(output_dir / "blind.json", packet)
    _exclusive(output_dir / "blind_manifest.json", manifest)
    return manifest


def _blind_read(locked: Path) -> tuple[dict, dict]:
    blob = (locked / "blind.json").read_bytes()
    manifest = _read(locked / "blind_manifest.json")
    if _sha(blob) != manifest["blind_sha256"]:
        raise TrialError("tampered blind packet")
    packet = json.loads(blob)
    if packet["run_id"] != manifest["run_id"] or packet["cutoff_utc"] != manifest["cutoff_utc"]:
        raise TrialError("blind manifest does not match packet")
    if _date(manifest["locked_at_utc"]) > _date(manifest["cutoff_utc"]):
        raise TrialError("blind lock occurred after cutoff")
    return packet, manifest


def _pct(v: float, series: list[float]) -> float:
    return sum(x <= v for x in series) / len(series)


def _with_digest(payload: dict) -> dict:
    return {"payload": payload, "sha256": _sha(_dump(payload))}


def _verify_digest(path: Path) -> dict:
    wrapped = _read(path)
    if _sha(_dump(wrapped["payload"])) != wrapped["sha256"]:
        raise TrialError(f"digest mismatch: {path}")
    return wrapped["payload"]


def freeze(locked: Path, market_path: Path, model_path: Path) -> dict:
    """Stage 2: admit prices only AFTER a durable, validated issuer lock."""
    if (locked / "trial_frozen.json").exists():
        raise TrialError("experiment Frozen is immutable")
    blind, manifest = _blind_read(locked)
    market, model = _read(market_path), _read(model_path)
    _keys(market, {"run_id", "cutoff_utc", "session1_date", "candidates"}, "market")
    _keys(model, {"run_id", "cutoff_utc", "asof_utc", "ranked"}, "model")
    run_id, cutoff_str = blind["run_id"], blind["cutoff_utc"]
    cutoff = _date(cutoff_str)
    if (market["run_id"], market["cutoff_utc"]) != (run_id, cutoff_str):
        raise TrialError("market cutoff/run ID mismatch")
    if (model["run_id"], model["cutoff_utc"]) != (run_id, cutoff_str):
        raise TrialError("model cutoff/run ID mismatch")
    et = cutoff.astimezone(ZoneInfo("America/New_York"))
    if et.strftime("%Y-%m-%d") != market["session1_date"] or (et.hour, et.minute) >= (9, 30):
        raise TrialError("only PREOPEN full-session comparison is safe with daily highs")
    model_asof = _date(model["asof_utc"])
    if not _date(manifest["locked_at_utc"]) <= model_asof <= cutoff:
        raise TrialError("AI model rank must be after blind lock and no later than cutoff")
    items = market["candidates"]
    if _canonical_set(items, "market") != _canonical_set(blind["candidates"], "issuer"):
        raise TrialError("issuer and market candidate universes differ")
    eligible: dict[str, dict] = {}
    excluded: dict[str, str] = {}
    for item in items:
        _keys(item, MARKET_FIELDS, f"market {item.get('ticker')}")
        t = _ticker(item)
        observation = _date(item["observed_at_utc"])
        if not cutoff - timedelta(minutes=15) <= observation <= cutoff:
            raise TrialError(f"{t} quote aged or after the cutoff")
        if item["source"] != "SIP":
            raise TrialError("only consolidated SIP prices permitted for comparable baseline")
        for field in ("last_price", "adtv20_usd", "momentum5_pct", "relative_volume20", "atr20_pct"):
            _number(item[field], field)
        if not isinstance(item["listing_sessions"], int) or isinstance(item["listing_sessions"], bool):
            raise TrialError("listing session count must be integer")
        if not isinstance(item["is_spac"], bool):
            raise TrialError("is_spac must be true/false, not UNKNOWN")
        why = []
        if item["exchange"] not in {"NASDAQ", "NYSE", "NYSEAMERICAN"}:
            why.append("EXCHANGE")
        if item["security_type"] not in {"COMMON_STOCK", "US_LISTED_ORDINARY"} or item["is_spac"]:
            why.append("SECURITY_TYPE_OR_SPAC")
        if item["last_price"] < 3 or item["adtv20_usd"] < 10_000_000 or item["listing_sessions"] < 20:
            why.append("PRICE_LIQUIDITY_OR_AGE")
        if item["relative_volume20"] < 0 or item["atr20_pct"] < 0:
            why.append("INVALID_FEATURE")
        if why:
            excluded[t] = "|".join(why)
        else:
            eligible[t] = item
    if len(eligible) < 20:
        raise TrialError("fewer than 20 fully verified eligible candidates")
    blind_by = {r["ticker"]: r for r in blind["candidates"]}
    scores_a = {}
    for t, x in eligible.items():
        scores_a[t] = round(sum((
            _pct(x["momentum5_pct"], [z["momentum5_pct"] for z in eligible.values()]),
            _pct(x["relative_volume20"], [z["relative_volume20"] for z in eligible.values()]),
            _pct(x["atr20_pct"], [z["atr20_pct"] for z in eligible.values()]),
        )), 8)
    scores_b = {
        t: 2 * blind_by[t]["novelty"] + 3 * blind_by[t]["expectation_delta"]
        + 2 * blind_by[t]["fundamental_impact"]
        for t in eligible
    }
    a = sorted(eligible, key=lambda t: (-scores_a[t], t))
    b = sorted(eligible, key=lambda t: (-scores_b[t], t))
    ranked = model["ranked"]
    if not isinstance(ranked, list):
        raise TrialError("model ranked must be array")
    c = []
    for row in ranked:
        _keys(row, {"ticker", "thesis", "counter"}, "model row")
        t = _ticker(row)
        if not str(row["thesis"]).strip() or not str(row["counter"]).strip():
            raise TrialError("model thesis and counter required")
        c.append(t)
    if len(c) != len(set(c)) or set(c) != set(eligible):
        raise TrialError("AI rank must cover EXACT SAME eligible candidate pool")
    portfolio = {key: {"ranks": rank, "top20": rank[:20], "top5": rank[:5]}
                 for key, rank in (("A_SIMPLE", a), ("B_ISSUER_EVENT", b), ("C_HASOL_AI", c))}
    payload = {
        "version": VERSION, "status": "EXPERIMENT_ONLY", "run_id": run_id,
        "cutoff_utc": cutoff_str, "session1_date": market["session1_date"],
        "blind_sha256": manifest["blind_sha256"],
        "market_sha256": _sha(market_path.read_bytes()),
        "model_sha256": _sha(model_path.read_bytes()),
        "candidate_n": len(items), "eligible_n": len(eligible), "excluded": excluded,
        "baseline": {t: {"price": x["last_price"], "observed_at_utc": x["observed_at_utc"],
                         "security_id": x["security_id"]} for t, x in eligible.items()},
        "portfolios": portfolio,
        "comparability": "SAME_ELIGIBLE_POOL_CUTOFF_PRICE_5_SESSION_TARGET",
        "actual_full_us_market_winner_ranks": "UNKNOWN",
        "upstream_price_blind_ai_exposure": "NOT_ATTESTED",
        "clean_forward_credit": False,
    }
    wrapped = _with_digest(payload)
    _exclusive(locked / "trial_frozen.json", wrapped)
    return wrapped


def review(frozen_path: Path, outcomes_path: Path, output_path: Path) -> dict:
    """Final S5 only; daily high +10% TOUCH, never use positive close as success."""
    frozen, raw = _verify_digest(frozen_path), _read(outcomes_path)
    _keys(raw, {"run_id", "asof_utc", "session_dates", "rows"}, "outcomes")
    if frozen["run_id"] != raw["run_id"]:
        raise TrialError("outcome run ID differs from Frozen")
    dates = raw["session_dates"]
    if len(dates) != 5 or dates != sorted(set(dates)) or dates[0] != frozen["session1_date"]:
        raise TrialError("exact five distinct ordered completed regular sessions required")
    last_close = datetime.fromisoformat(dates[-1]).replace(tzinfo=ZoneInfo("America/New_York"))
    last_close = last_close.replace(hour=16, minute=0)
    if _date(raw["asof_utc"]) < last_close.astimezone(UTC):
        raise TrialError("S5 session has not closed")
    if _date(raw["asof_utc"]) > datetime.now(UTC):
        raise TrialError("outcome data timestamp is in the future")
    pool = set(frozen["baseline"])
    if _canonical_set(raw["rows"], "outcomes") != pool:
        raise TrialError("outcome universe differs from original eligible set")
    stats = {}
    for row in raw["rows"]:
        _keys(row, {"ticker", "source", "bars"}, "outcome row")
        if row["source"] != "SIP" or len(row["bars"]) != 5:
            raise TrialError("five consolidated SIP bars are mandatory")
        highs, closes = [], []
        for bar, date in zip(row["bars"], dates):
            _keys(bar, {"date", "high", "close"}, "outcome daily bar")
            if bar["date"] != date:
                raise TrialError("missing/misaligned daily date")
            highs.append(_number(bar["high"], "high", low=0))
            closes.append(_number(bar["close"], "close", low=0))
            if closes[-1] > highs[-1]:
                raise TrialError("close exceeds session high")
        px = frozen["baseline"][row["ticker"]]["price"]
        first = next((i + 1 for i, h in enumerate(highs) if h >= px * 1.1 - 1e-9), None)
        stats[row["ticker"]] = {
            "first_hit_session": first, "hit10_s5": first is not None,
            "peak_pct": round(100 * (max(highs) / px - 1), 5),
            "last_close_pct": round(100 * (closes[-1] / px - 1), 5),
        }
    actual = sorted(pool, key=lambda t: (-stats[t]["peak_pct"], t))
    summaries = {}
    for name, p in frozen["portfolios"].items():
        top20, top5 = p["top20"], p["top5"]
        summaries[name] = {
            "top20_hits": sum(stats[t]["hit10_s5"] for t in top20),
            "top5_hits": sum(stats[t]["hit10_s5"] for t in top5),
            "top20_mean_close_pct": round(sum(stats[t]["last_close_pct"] for t in top20) / 20, 5),
            "top5_mean_close_pct": round(sum(stats[t]["last_close_pct"] for t in top5) / 5, 5),
            "within_original_cohort_top20_overlap": len(set(top20) & set(actual[:20])),
            "within_original_cohort_top5_overlap": len(set(top5) & set(actual[:5])),
        }
    result = {
        "status": "EXPERIMENT_ONLY_S5", "run_id": raw["run_id"],
        "frozen_sha256": _sha(frozen_path.read_bytes()),
        "outcomes_sha256": _sha(outcomes_path.read_bytes()),
        "candidate_pool_n": len(pool), "session_dates": dates,
        "comparison": summaries, "candidate_results": stats,
        "actual_top20_scope": "ORIGINAL_ELIGIBLE_COHORT_ONLY_NOT_FULL_US_MARKET",
        "clean_forward_credit": False,
    }
    _exclusive(output_path, _with_digest(result))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    x = sub.add_parser("lock")
    x.add_argument("--issuer", required=True, type=Path)
    x.add_argument("--out", required=True, type=Path)
    x = sub.add_parser("freeze")
    x.add_argument("--locked", required=True, type=Path)
    x.add_argument("--market", required=True, type=Path)
    x.add_argument("--model", required=True, type=Path)
    x = sub.add_parser("review")
    x.add_argument("--frozen", required=True, type=Path)
    x.add_argument("--outcomes", required=True, type=Path)
    x.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.cmd == "lock":
        result = lock_issuer(args.issuer, args.out)
    elif args.cmd == "freeze":
        result = freeze(args.locked, args.market, args.model)
    else:
        result = review(args.frozen, args.outcomes, args.out)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
