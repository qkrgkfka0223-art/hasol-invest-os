"""Read-only pre-Frozen audit of issuer freshness and market-discovery provenance.

Inputs MUST be captured in the live run. This code cannot certify that a feed
actually covered all US issuers; external verification is still required.
No live data requests, no mutation of historical Frozen, no secret management.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path


def parse_time(value, label):
    try:
        t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if t.tzinfo is None:
            raise ValueError("naive")
        return t.astimezone(timezone.utc)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}: timezone-aware timestamp required") from exc


def parse_date(value, label):
    try:
        d = date.fromisoformat(value)
        if d.isoformat() != value:
            raise ValueError()
        return d
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError(f"{label}: YYYY-MM-DD required") from exc


def audit(snapshot):
    errors, degraded, notices = [], [], []
    if not isinstance(snapshot, dict):
        return {"decision": "BLOCK", "errors": ["root must be an object"], "degraded": []}
    if snapshot.get("schema") != "HASOL-PREFREEZE-v1":
        errors.append("incorrect schema")
    if not str(snapshot.get("run_id") or "").strip():
        errors.append("run_id missing")
    try:
        cutoff = parse_time(snapshot.get("cutoff_utc"), "cutoff_utc")
        lock = parse_time(snapshot.get("blind_locked_at_utc"), "blind_locked_at_utc")
        first_price = parse_time(snapshot.get("first_price_exposure_at_utc"), "first_price_exposure_at_utc")
        if not lock <= first_price <= cutoff:
            degraded.append("price exposure or blind lock chronology not clean")
        prior_day = parse_date(snapshot.get("last_completed_regular_session"), "last_completed_regular_session")
        run_date = parse_date(snapshot.get("run_market_date"), "run_market_date")
        if prior_day >= run_date:
            errors.append("last completed market session must predate run date")
    except ValueError as exc:
        errors.append(str(exc))
        cutoff = lock = first_price = prior_day = run_date = None

    for key in ("candidate_packets", "issuer_releases", "issuer_sweeps", "lagged_leader_batches", "live_mover_snapshots"):
        if not isinstance(snapshot.get(key), list):
            errors.append(f"{key} must be an array")
    if errors:
        return {"decision": "BLOCK", "errors": sorted(set(errors)), "degraded": sorted(set(degraded))}

    packets = {}
    for i, row in enumerate(snapshot["candidate_packets"]):
        if not isinstance(row, dict):
            errors.append(f"candidate_packets[{i}] invalid")
            continue
        ticker = str(row.get("ticker") or "").strip().upper()
        if not ticker or ticker in packets:
            errors.append(f"candidate_packets[{i}] ticker missing/duplicate")
        else:
            packets[ticker] = row
        for field in ("discovered_at_utc",):
            try:
                at = parse_time(row.get(field), f"{ticker}.{field}")
                if at > cutoff:
                    errors.append(f"{ticker}: candidate from after cutoff (lookahead)")
            except ValueError as exc:
                errors.append(str(exc))

    release_ids = set()
    handled_material = 0
    for i, row in enumerate(snapshot["issuer_releases"]):
        if not isinstance(row, dict):
            errors.append(f"issuer_releases[{i}] invalid")
            continue
        rid = str(row.get("release_id") or "")
        ticker = str(row.get("ticker") or "").upper().strip()
        if not rid or rid in release_ids or not ticker:
            errors.append(f"issuer_releases[{i}] invalid/duplicate release id or ticker")
            continue
        release_ids.add(rid)
        try:
            published = parse_time(row.get("published_at_utc"), f"{rid}.published_at_utc")
            collected = parse_time(row.get("collected_at_utc"), f"{rid}.collected_at_utc")
            if published > collected or collected > cutoff:
                errors.append(f"{rid}: event or collection lookahead")
                continue
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not str(row.get("primary_url") or "").startswith("https://"):
            degraded.append(f"{rid}: primary issuer URL missing")
        if row.get("source_verified") is not True or row.get("full_original_checked") is not True:
            degraded.append(f"{rid}: original publication not independently verified")
        if not isinstance(row.get("material"), bool):
            errors.append(f"{rid}: materiality not a verified Boolean")
            continue
        if row["material"] is False:
            continue
        if published <= cutoff:
            packet = packets.get(ticker)
            if not packet or not isinstance(packet.get("handled_release_ids"), list) or rid not in packet["handled_release_ids"]:
                errors.append(f"{rid}: MATERIAL_ISSUER_RELEASE_NOT_HANDLED for {ticker} before freeze")
            else:
                handled_material += 1
                try:
                    considered_at = parse_time(packet.get("last_issuer_review_at_utc"), f"{ticker}.last_issuer_review_at_utc")
                    if considered_at < published or considered_at > cutoff:
                        errors.append(f"{rid}: issuer event was not actually reconsidered before cutoff")
                    if published > lock:
                        degraded.append(f"{rid}: new material event after Price-Blind lock; cannot claim clean blind")
                except ValueError as exc:
                    degraded.append(str(exc))

    before_blind = False
    recent_precommit = False
    for i, row in enumerate(snapshot["issuer_sweeps"]):
        if not isinstance(row, dict):
            errors.append(f"issuer_sweeps[{i}] invalid")
            continue
        try:
            at = parse_time(row.get("completed_at_utc"), f"issuer_sweeps[{i}].completed_at_utc")
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if at > cutoff:
            errors.append("issuer sweep performed after cutoff (lookahead)")
        if row.get("primary_issuer_only") is not True or row.get("price_reaction_preview") is not False:
            degraded.append("issuer sweep not source-only/price-free")
        if row.get("feed_coverage_verified") is not True:
            degraded.append("issuer source coverage not verified")
        if at <= lock:
            before_blind = True
        if lock < at <= cutoff and 0 <= (cutoff - at).total_seconds() <= 900:
            recent_precommit = True
    if not before_blind:
        degraded.append("no completed issuer-only sweep before blind lock")
    if not recent_precommit:
        degraded.append("no issuer freshness recheck in last 15 minutes before cutoff")

    lagged_sets = []
    for i, batch in enumerate(snapshot["lagged_leader_batches"]):
        try:
            session = parse_date(batch.get("session_date"), f"lagged_batch[{i}].session_date")
            stamped = parse_time(batch.get("available_at_utc"), f"lagged_batch[{i}].available_at_utc")
            if session > prior_day or session >= run_date or stamped > cutoff:
                errors.append("lagged winners contain current-day or future data")
            tickers = batch.get("tickers")
            if not isinstance(tickers, list) or len(tickers) > 100 or any(not isinstance(x, str) for x in tickers) or len(tickers) != len(set(tickers)):
                errors.append("lagged Top100 batch malformed")
            else:
                if batch.get("publisher_data_verified") is not True:
                    degraded.append("lagged Top100 provider completeness not independently verified")
                if len(tickers) != 100:
                    degraded.append("lagged Top100 batch has fewer than 100 verified tickers")
                lagged_sets.extend(tickers)
        except (ValueError, TypeError, AttributeError) as exc:
            errors.append(f"lagged batch bad: {exc}")
    if not snapshot["lagged_leader_batches"]:
        degraded.append("prior-session Top100 discovery shadow absent")
    elif not isinstance(snapshot.get("shadow_discovery_tickers"), list) or not set(lagged_sets).issubset(set(str(x).upper() for x in snapshot["shadow_discovery_tickers"])):
        degraded.append("lagged Top100 not fully carried into shadow candidate pool")
    notices.append("Lagged Top100 is discovery SHADOW only; never automatic Top20")

    for i, snap in enumerate(snapshot["live_mover_snapshots"]):
        try:
            at = parse_time(snap.get("asof_utc"), f"live_mover_snapshots[{i}].asof_utc")
            if at > cutoff:
                errors.append("live mover snapshot from after cutoff (lookahead)")
            if at < lock:
                degraded.append("live movers observed before physical blind lock")
            if snap.get("discovery_class") != "AFTER_PRICE_DISCOVERY":
                degraded.append("live mover snapshot not tagged AFTER_PRICE_DISCOVERY")
        except (ValueError, TypeError, AttributeError) as exc:
            errors.append(f"live mover snapshot invalid: {exc}")

    if snapshot.get("full_pit_eligible_roster_verified") is not True:
        degraded.append("full same-cutoff PIT eligible universe UNKNOWN; no full-market winner recall claim")
    if snapshot.get("release_feed_completeness_independently_confirmed") is not True:
        degraded.append("complete issuer release feed not independently demonstrated")

    return {
        "decision": "BLOCK" if errors else ("OFFICIAL_PARTIAL_NOT_CLEAN" if degraded else "EVIDENCE_READY_REQUIRES_INDEPENDENT_VERIFY"),
        "errors": sorted(set(errors)),
        "degraded": sorted(set(degraded)),
        "notices": notices,
        "metrics": {
            "candidate_packets": len(packets),
            "issuer_releases_observed": len(release_ids),
            "material_releases_handled": handled_material,
            "lagged_shadow_union_n": len(set(lagged_sets)),
            "external_market_or_issuer_data_authenticated_by_this_script": False,
        },
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="Fail-closed HASOL source freshness/discovery audit")
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path)
    p.add_argument("--require-evidence-ready", action="store_true")
    args = p.parse_args(argv)
    result = audit(json.loads(args.input.read_text(encoding="utf-8")))
    content = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(content, encoding="utf-8")
    print(content, end="")
    return 2 if result["decision"] == "BLOCK" else (3 if args.require_evidence_ready and result["decision"] != "EVIDENCE_READY_REQUIRES_INDEPENDENT_VERIFY" else 0)


if __name__ == "__main__":
    sys.exit(main())
