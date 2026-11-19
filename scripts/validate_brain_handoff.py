"""Fail-closed audit for a HASOL Brain-to-GitHub checkpoint.

Consumes a JSON snapshot exported from HASOL_EXTERNAL_BRAIN by an authorized
operator/connector. Never reads the market or mutates Google Sheets/Frozen.
A clean *candidate* means the supplied evidence is internally consistent;
the tool cannot authenticate external issuers or market feeds.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "HASOL-BRAIN-HANDOFF-v1"
VENUES = {"NASDAQ", "NYSE", "AMEX"}
TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,14}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _time(value, field):
    try:
        d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if d.tzinfo is None:
            raise ValueError("timezone missing")
        return d.astimezone(timezone.utc)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{field}: timezone-aware ISO timestamp required") from exc


def _number(value, field):
    if isinstance(value, bool):
        raise ValueError(f"{field}: numeric value required")
    try:
        v = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field}: numeric value required") from exc
    if not math.isfinite(v):
        raise ValueError(f"{field}: finite number required")
    return v


def _flag(value):
    return value is True or str(value).upper() in {"TRUE", "YES"}


def _index(rows, field, errors, group):
    if not isinstance(rows, list):
        errors.append(f"{group}: expected list")
        return {}
    found = {}
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"{group}[{i}]: expected object")
            continue
        ticker = str(row.get(field, "")).strip().upper()
        if not TICKER_RE.fullmatch(ticker):
            errors.append(f"{group}[{i}]: invalid {field}")
        elif ticker in found:
            errors.append(f"{group}: duplicate ticker {ticker}")
        else:
            found[ticker] = row
    return found


def _is_primary_issuer(row, blind_lock, degraded, ticker):
    origin = str(row.get("DISCOVERY_CLASS", ""))
    if origin != "ISSUER_PRIMARY_RELEASE":
        degraded.append(f"{ticker}: original issuer-first discovery not proven ({origin or 'UNKNOWN'})")
        return
    if not _flag(row.get("source_independently_verified")):
        degraded.append(f"{ticker}: primary source not independently verified")
    ref = str(row.get("SOURCE_REF") or "")
    if not ref.startswith("https://"):
        degraded.append(f"{ticker}: missing HTTPS primary issuer URL")
    source_times = {}
    for field in ("ISSUER_RELEASED_AT_UTC", "BLIND_PACKET_AT_UTC"):
        try:
            when = _time(row.get(field), field)
        except ValueError:
            degraded.append(f"{ticker}: {field} missing/invalid")
        else:
            source_times[field] = when
            if when > blind_lock:
                degraded.append(f"{ticker}: {field} later than blind lock")
    if (source_times.get("ISSUER_RELEASED_AT_UTC") and source_times.get("BLIND_PACKET_AT_UTC")
            and source_times["ISSUER_RELEASED_AT_UTC"] > source_times["BLIND_PACKET_AT_UTC"]):
        degraded.append(f"{ticker}: issuer publication later than supposedly blind packet (look-ahead)")
    if not str(row.get("BLIND_FACTS_SUMMARY") or "").strip():
        degraded.append(f"{ticker}: absent original issuer facts")
    if not str(row.get("BLIND_JUDGMENT") or "").strip():
        degraded.append(f"{ticker}: absent pre-price independent judgment")


def validate(snapshot):
    """Return deterministic audit output. No network, hindsight, or sheet writes."""
    errors, degraded, notes = [], [], []
    if not isinstance(snapshot, dict):
        return {"schema": SCHEMA, "decision": "BLOCK", "errors": ["root: expected object"], "degraded": [], "notes": []}
    if snapshot.get("schema") != SCHEMA:
        errors.append(f"unsupported schema (expected {SCHEMA})")
    run_id = str(snapshot.get("run_id") or "").strip()
    if not run_id:
        errors.append("run_id missing")

    p = _index(snapshot.get("predictions"), "TICKER_SNAPSHOT", errors, "predictions")
    f = _index(snapshot.get("frozen"), "TICKER_SNAPSHOT", errors, "frozen")
    o = _index(snapshot.get("outcomes"), "TICKER_SNAPSHOT", errors, "outcomes")
    ranked = []
    for ticker, row in p.items():
        if row.get("RUN_ID") != run_id:
            errors.append(f"{ticker}: prediction RUN_ID mismatch")
        raw_rank = row.get("OFFICIAL_MODEL_RANK")
        if raw_rank is None or str(raw_rank).strip() == "":
            continue  # discovered but not evaluated; never treat as rank zero
        try:
            rank = _number(raw_rank, f"{ticker}.OFFICIAL_MODEL_RANK")
            if not rank.is_integer() or rank <= 0:
                raise ValueError()
            ranked.append(int(rank))
        except ValueError:
            errors.append(f"{ticker}: invalid OFFICIAL_MODEL_RANK")
    if len(ranked) < 40:
        degraded.append(f"evaluated frontier below target 40 ({len(ranked)})")
    if len(ranked) <= 20:
        errors.append("evaluated frontier must exceed Top20")
    if sorted(ranked) != list(range(1, len(ranked) + 1)):
        errors.append("official ranked frontier is not unique and contiguous 1..N")
    if len(f) != 20 or len(o) != 20:
        errors.append(f"Frozen/Outcome cardinality must be 20/20 (found {len(f)}/{len(o)})")
    flagged_20 = {t for t, r in p.items() if _flag(r.get("MODEL_TOP20"))}
    flagged_5 = {t for t, r in p.items() if _flag(r.get("TOP5"))}
    if len(flagged_20) != 20 or len(flagged_5) != 5 or not flagged_5.issubset(flagged_20):
        errors.append("Prediction Top20/Top5 flags must be 20/5 and Top5 subset")
    selected_ranked = {t for t, r in p.items() if str(r.get("OFFICIAL_MODEL_RANK") or "") in {str(i) for i in range(1, 21)}}
    if flagged_20 != selected_ranked:
        errors.append("Prediction Top20 flags differ from official rank 1..20")
    if {t for t, r in p.items() if str(r.get("OFFICIAL_MODEL_RANK") or "") in {"1", "2", "3", "4", "5"}} != flagged_5:
        errors.append("Prediction Top5 flags differ from official rank 1..5")

    freeze_times = set()
    frozen_top5 = set()
    stale = []
    for ticker, row in f.items():
        if row.get("RUN_ID") != run_id:
            errors.append(f"{ticker}: Frozen RUN_ID mismatch")
        try:
            rank = _number(row.get("RANK"), f"{ticker}.RANK")
            price = _number(row.get("BASELINE_PRICE"), f"{ticker}.BASELINE_PRICE")
            if not rank.is_integer() or rank < 1 or rank > 20 or price <= 0:
                raise ValueError()
        except ValueError:
            errors.append(f"{ticker}: invalid frozen rank/price")
            continue
        if row.get("LOCK") != "LOCKED":
            errors.append(f"{ticker}: Frozen not LOCKED")
        if _flag(row.get("TOP5")):
            frozen_top5.add(ticker)
        if ticker not in p or ticker not in o:
            errors.append(f"{ticker}: missing Prediction or Outcome")
            continue
        try:
            original_rank = _number(p[ticker].get("OFFICIAL_MODEL_RANK"), f"{ticker}.OFFICIAL_MODEL_RANK")
            if not _flag(p[ticker].get("MODEL_TOP20")) or rank != original_rank:
                errors.append(f"{ticker}: prediction rank/flag parity failure")
        except ValueError:
            errors.append(f"{ticker}: malformed prediction rank/flag parity")
        try:
            orank = _number(o[ticker].get("RANK"), f"{ticker}.OUTCOME.RANK")
            oprice = _number(o[ticker].get("BASELINE_PRICE"), f"{ticker}.OUTCOME.BASELINE_PRICE")
            if orank != rank or oprice != price or o[ticker].get("RUN_ID") != run_id:
                errors.append(f"{ticker}: Outcome rank/baseline/run mismatch")
        except ValueError:
            errors.append(f"{ticker}: Outcome rank/baseline invalid")

        try:
            when = _time(row.get("FROZEN_AT_UTC"), "FROZEN_AT_UTC")
            observed = _time(row.get("BASELINE_OBSERVED_AT_UTC"), "BASELINE_OBSERVED_AT_UTC")
            freeze_times.add(when.isoformat())
            age = (when - observed).total_seconds()
            if age < 0 or age > 180:
                stale.append(ticker)
                degraded.append(f"{ticker}: original baseline age {age:.1f}s outside 0..180s")
        except ValueError:
            degraded.append(f"{ticker}: baseline/freeze timestamp missing")
        if not str(row.get("PRICE_SOURCE") or "").strip():
            degraded.append(f"{ticker}: original quote provider missing")
        e = row.get("eligibility")
        if not isinstance(e, dict):
            errors.append(f"{ticker}: selected security eligibility missing")
        else:
            try:
                ok = (
                    str(e.get("exchange", "")).upper() in VENUES
                    and str(e.get("security_type", "")).upper() == "COMMON_STOCK"
                    and _number(e.get("listed_sessions"), "listed_sessions") >= 20
                    and _number(e.get("price"), "eligibility_price") >= 3
                    and _number(e.get("adtv20_usd"), "adtv20_usd") >= 10_000_000
                )
                if not ok:
                    errors.append(f"{ticker}: selected security fails eligibility")
            except ValueError:
                errors.append(f"{ticker}: selected security eligibility unverified")
    if len(freeze_times) != 1:
        errors.append("Frozen rows do not share one valid freeze timestamp")
    if {t for t in f if t in flagged_20} != flagged_20 or frozen_top5 != flagged_5:
        errors.append("Frozen membership/Top5 differs from Prediction")
    frozen_ranks = [str(x.get("RANK") or "") for x in f.values()]
    if sorted(frozen_ranks, key=lambda x: int(x) if x.isdigit() else 999) != [str(i) for i in range(1, 21)]:
        errors.append("Frozen ranks are not exactly 1..20")
    if set(f) != set(o):
        errors.append("Frozen/Outcome ticker sets differ")

    lock = None
    try:
        lock = _time(snapshot.get("blind_locked_at_utc"), "blind_locked_at_utc")
        market = _time(snapshot.get("first_market_data_access_at_utc"), "first_market_data_access_at_utc")
        if market < lock:
            degraded.append("market/price exposure preceded durable blind lock")
        if freeze_times and market > _time(next(iter(freeze_times)), "FROZEN_AT_UTC"):
            degraded.append("first market data access after Frozen timestamp")
    except ValueError:
        degraded.append("blind/market access chronological evidence missing")
    if lock is not None:
        for ticker in flagged_20:
            if ticker in p:
                _is_primary_issuer(p[ticker], lock, degraded, ticker)

    u = snapshot.get("universe")
    if not isinstance(u, dict) or u.get("complete") is not True:
        degraded.append("same-cutoff full point-in-time eligible universe UNKNOWN")
    else:
        sha = str(u.get("snapshot_sha256") or "").lower()
        if not SHA256_RE.fullmatch(sha):
            degraded.append("full PIT universe snapshot SHA256 absent/invalid")
        try:
            captured = _time(u.get("asof_utc"), "universe.asof_utc")
            if freeze_times and captured > _time(next(iter(freeze_times)), "FROZEN_AT_UTC"):
                degraded.append("universe snapshot after Frozen")
        except ValueError:
            degraded.append("PIT universe snapshot timestamp missing")
        if not _flag(u.get("independently_verified")):
            degraded.append("full PIT roster completeness not independently verified")

    shadow = snapshot.get("shadow") or {}
    if shadow.get("status") != "SCORABLE":
        notes.append("SIMPLE_ATR20_V1 shadow UNSCORABLE; never backfill after outcomes")
    else:
        if shadow.get("method") != "SIMPLE_ATR20_V1":
            degraded.append("shadow uses unregistered method")
        try:
            scored_at = _time(shadow.get("scored_at_utc"), "shadow.scored_at_utc")
            if freeze_times and scored_at > _time(next(iter(freeze_times)), "FROZEN_AT_UTC"):
                degraded.append("shadow scored after Frozen")
        except ValueError:
            degraded.append("shadow pre-Frozen timestamp missing")
        scored = shadow.get("scores")
        if not isinstance(scored, list) or len(scored) != len(ranked):
            degraded.append("shadow candidate count does not match evaluated frontier")
        else:
            try:
                names = [str(s["ticker"]).upper() for s in scored]
                ranks = [int(_number(s["rank"], "shadow.rank")) for s in scored]
                values = [_number(s["score"], "shadow.score") for s in scored]
                if len(set(names)) != len(names) or set(names) != {t for t, pr in p.items() if str(pr.get("OFFICIAL_MODEL_RANK") or "").isdigit() and int(pr["OFFICIAL_MODEL_RANK"])>0}:
                    degraded.append("shadow universe differs from model evaluated frontier")
                if sorted(ranks) != list(range(1, len(ranks) + 1)):
                    degraded.append("shadow ranks not unique/contiguous")
                expected = sorted(zip(names, values), key=lambda x: (-x[1], x[0]))
                actual = [name for _, name in sorted(zip(ranks, names))]
                if actual != [name for name, _ in expected]:
                    degraded.append("shadow ranking not score-desc / ticker-asc deterministic")
            except (ValueError, KeyError, TypeError):
                degraded.append("shadow score fields invalid")

    decision = "BLOCK" if errors else ("OFFICIAL_PARTIAL_NOT_CLEAN" if degraded else "EVIDENCE_READY_REQUIRES_INDEPENDENT_VERIFY")
    return {
        "schema": SCHEMA,
        "run_id": run_id,
        "decision": decision,
        "errors": sorted(set(errors)),
        "degraded": sorted(set(degraded)),
        "notes": notes,
        "metrics": {
            "predictions": len(p),
            "ranked": len(ranked),
            "frozen": len(f),
            "outcomes": len(o),
            "top5": len(frozen_top5),
            "stale_baseline_count": len(stale),
            "universe_verified_from_live_source": False,
            "external_issuer_source_verified_by_this_script": False,
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate HASOL Brain handoff JSON without touching official Frozen")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--require-evidence-ready", action="store_true")
    parser.add_argument("--source-audit-input", type=Path, default=None,
                        help="same-run source freshness/discovery JSON; required for strict evidence-ready")
    args = parser.parse_args(argv)
    data = json.loads(args.input.read_text(encoding="utf-8"))
    result = validate(data)
    if args.source_audit_input:
        from scripts.audit_discovery_freshness import audit as audit_source, parse_time
        try:
            source = json.loads(args.source_audit_input.read_text(encoding="utf-8"))
            source_result = audit_source(source)
            result["source_audit"] = source_result
            if source_result["decision"] == "BLOCK":
                result["errors"].extend("source: " + e for e in source_result["errors"])
            if str(source.get("run_id") or "") != str(result.get("run_id") or ""):
                result["errors"].append("source: RUN_ID mismatch")
            try:
                freeze = parse_time(data["frozen"][0]["FROZEN_AT_UTC"], "FROZEN_AT_UTC")
                cutoff = parse_time(source.get("cutoff_utc"), "source.cutoff_utc")
                if cutoff > freeze:
                    result["errors"].append("source: audit cutoff after Frozen (lookahead)")
            except (KeyError, IndexError, TypeError, ValueError):
                result["errors"].append("source: cannot verify source-to-Frozen cutoff")
            result["degraded"].extend("source: " + e for e in source_result["degraded"])
            if not result["errors"] and source_result["decision"] != "EVIDENCE_READY_REQUIRES_INDEPENDENT_VERIFY":
                result["degraded"].append("source: freshness/discovery not evidence-ready")
        except (OSError, ValueError, TypeError) as exc:
            result["errors"].append("source audit unreadable or invalid: " + str(exc))
    elif args.require_evidence_ready:
        result["degraded"].append("source freshness/discovery gate omitted; strict clean impossible")
    result["errors"] = sorted(set(result["errors"]))
    result["degraded"] = sorted(set(result["degraded"]))
    result["decision"] = ("BLOCK" if result["errors"] else
                          "OFFICIAL_PARTIAL_NOT_CLEAN" if result["degraded"] else
                          "EVIDENCE_READY_REQUIRES_INDEPENDENT_VERIFY")
    payload = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    if result["decision"] == "BLOCK":
        return 2
    if args.require_evidence_ready and result["decision"] != "EVIDENCE_READY_REQUIRES_INDEPENDENT_VERIFY":
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
