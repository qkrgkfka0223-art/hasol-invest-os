"""Read-only, forward-safe HASOL failure attribution and learning audit.

SHADOW only. Inputs are independently captured frozen snapshots, issuer
release evidence and completed US regular-session bars. Never rewrites Frozen
or upgrades a production rule. UNKNOWN is the default for missing evidence.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date, datetime, timezone
from pathlib import Path

SCHEMA = "HASOL-LEARNING-AUDIT-v1"
UNKNOWN = "UNKNOWN"


def moment(value):
    try:
        d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if d.tzinfo is None:
            raise ValueError("timezone missing")
        return d.astimezone(timezone.utc)
    except (TypeError, ValueError) as exc:
        raise ValueError("timezone-aware timestamp required") from exc


def session_day(value):
    try:
        d = date.fromisoformat(str(value))
        if d.isoformat() != value:
            raise ValueError("not canonical")
        return d
    except (ValueError, TypeError) as exc:
        raise ValueError("YYYY-MM-DD required") from exc


def positive(value):
    if isinstance(value, bool):
        raise ValueError("boolean is not numeric")
    try:
        x = float(value)
        if not math.isfinite(x) or x <= 0:
            raise ValueError("not finite positive")
        return x
    except (ValueError, TypeError) as exc:
        raise ValueError("finite positive number required") from exc


def index(rows, label, errors):
    if not isinstance(rows, list):
        errors.append(f"{label}: list required")
        return {}
    out = {}
    for row in rows:
        if not isinstance(row, dict) or not str(row.get("ticker") or "").strip():
            errors.append(f"{label}: invalid row")
            continue
        t = str(row["ticker"]).upper().strip()
        if t in out:
            errors.append(f"{label}: duplicate ticker {t}")
        else:
            out[t] = row
    return out


def audit(data):
    errors, gaps, events = [], [], []
    if not isinstance(data, dict):
        return {"decision": "BLOCK", "errors": ["root must be object"]}
    if data.get("schema") != SCHEMA:
        errors.append("schema mismatch")
    run_id = str(data.get("run_id") or "").strip()
    if not run_id:
        errors.append("run_id required")
    try:
        freeze_at = moment(data.get("freeze_at_utc"))
        asof = moment(data.get("audit_asof_utc"))
        blind_lock = moment(data.get("blind_locked_at_utc"))
        if not blind_lock <= freeze_at <= asof:
            errors.append("invalid blind/freeze/audit time order")
        last_completed = session_day(data.get("last_completed_regular_session"))
        session_dates = [session_day(v) for v in data.get("five_regular_sessions", [])]
        if len(session_dates) != 5 or sorted(set(session_dates)) != session_dates:
            errors.append("exactly five ordered unique US regular session dates required")
    except (ValueError, TypeError) as exc:
        errors.append(str(exc))
        freeze_at = asof = blind_lock = last_completed = None
        session_dates = []
    frozen = index(data.get("frozen"), "frozen", errors)
    candidates = index(data.get("candidate_packets"), "candidate_packets", errors)
    shadow = index(data.get("atr_shadow"), "atr_shadow", errors)
    if not isinstance(data.get("daily_bars"), list):
        errors.append("daily_bars must be list")
    if not isinstance(data.get("issuer_releases"), list):
        errors.append("issuer_releases must be list")
    if errors:
        return {"decision": "BLOCK", "errors": sorted(set(errors)), "gaps": []}
    if len(frozen) != 20:
        errors.append("immutable Frozen must have 20 unique tickers")
    ranks = []
    top5 = []
    stale = []
    for ticker, row in frozen.items():
        if row.get("run_id") != run_id or row.get("lock") != "LOCKED":
            errors.append(f"{ticker}: wrong run or not locked")
        try:
            rank = int(row["rank"])
            if str(rank) != str(row["rank"]) or rank < 1:
                raise ValueError()
            ranks.append(rank)
            if rank <= 5:
                top5.append(ticker)
            px = positive(row["baseline_price"])
            observed = moment(row["baseline_observed_at_utc"])
            if not observed <= freeze_at:
                errors.append(f"{ticker}: price after freeze")
            if (freeze_at - observed).total_seconds() > 180:
                stale.append(ticker)
            if row.get("row_hash") != row.get("outcome_row_hash"):
                errors.append(f"{ticker}: Frozen vs Outcome original hash mismatch")
            if abs(px - positive(row.get("outcome_baseline_price"))) > 1e-8:
                errors.append(f"{ticker}: Frozen vs Outcome original price mismatch")
        except (ValueError, KeyError, TypeError):
            errors.append(f"{ticker}: malformed original Frozen baseline/rank")
    if sorted(ranks) != list(range(1, 21)):
        errors.append("Frozen ranks must be 1..20")
    if len(top5) != 5:
        errors.append("Frozen Top5 cardinality mismatch")
    if errors:
        return {"decision": "BLOCK", "errors": sorted(set(errors)), "gaps": []}
    if stale:
        gaps.append("original observed Frozen trade older than 180 seconds: " + ", ".join(sorted(stale)))
    if data.get("source_feed_coverage_verified") is not True:
        gaps.append("complete primary issuer feed coverage UNKNOWN")
    if data.get("full_pit_eligible_roster_verified") is not True:
        gaps.append("full point-in-time eligible universe UNKNOWN")
    if data.get("security_eligibility_verified") is not True:
        gaps.append("US common-stock eligibility and 20D ADTV completeness UNKNOWN")

    daily = {}
    for i, row in enumerate(data["daily_bars"]):
        try:
            t = str(row["ticker"]).upper()
            day = session_day(row["session_date"])
            if t not in frozen or day not in session_dates:
                errors.append(f"daily_bars[{i}]: outside original Frozen/session scope")
                continue
            if day > last_completed:
                errors.append(f"daily_bars[{i}]: future session look-ahead")
                continue
            high = positive(row["regular_high"])
            close = positive(row["regular_close"])
            if high < close:
                errors.append(f"daily_bars[{i}]: high below close")
            key = (t, day)
            if key in daily:
                errors.append(f"daily_bars[{i}]: duplicate ticker/day")
            daily[key] = (high, close)
        except (KeyError, ValueError, TypeError) as exc:
            errors.append(f"daily_bars[{i}]: malformed ({exc})")
    completed = [d for d in session_dates if d <= last_completed]
    if len(completed) == 5:
        maturity = "S5_MATURED"
    else:
        maturity = f"S{len(completed)}_INTERIM"
    if not completed:
        gaps.append("no completed regular session yet")
    for day in completed:
        missing = [t for t in frozen if (t, day) not in daily]
        if missing:
            gaps.append(f"{day}: {len(missing)} selected ticker daily bars unavailable")
    if errors:
        return {"decision": "BLOCK", "errors": sorted(set(errors)), "gaps": sorted(set(gaps))}

    selected_hits = []
    day1_hits = []
    for t, row in frozen.items():
        base = float(row["baseline_price"])
        valid = [(day, daily[(t, day)]) for day in completed if (t, day) in daily]
        if valid and valid[0][0] == session_dates[0] and valid[0][1][0] >= base * 1.1:
            day1_hits.append(t)
        if any(v[0] >= base * 1.1 for _, v in valid):
            selected_hits.append(t)
    top5_set = set(top5)

    for row in data["issuer_releases"]:
        if not isinstance(row, dict):
            errors.append("issuer_releases: invalid record")
            continue
        try:
            published = moment(row["published_at_utc"])
            collected = moment(row["collected_at_utc"])
            if published > collected or collected > asof:
                errors.append("issuer release publish/collect look-ahead")
                continue
            ticker = str(row["ticker"]).upper()
            release_id = str(row["release_id"])
            material = row["material"]
            if type(material) is not bool or not release_id:
                errors.append("issuer release needs original ID and verified materiality boolean")
                continue
        except (KeyError, ValueError, TypeError) as exc:
            errors.append(f"issuer_releases: malformed ({exc})")
            continue
        if published > freeze_at or not material:
            continue
        if row.get("primary_full_text_verified") is not True:
            gaps.append(f"{release_id}: full original primary-source evidence not verified")
            continue
        packet = candidates.get(ticker)
        if packet is None:
            first = "DISCOVERY_FAIL"
        elif release_id not in packet.get("handled_release_ids", []):
            first = "CATALYST / DRIVER_ERROR"
        elif ticker not in frozen and packet.get("official_rank") is None:
            first = "MODEL_RANK_ERROR_POSSIBLE_NOT_PROVEN"
        else:
            first = None
        if first:
            events.append({
                "ticker": ticker, "release_id": release_id,
                "first_known_failure": first,
                "retrospective_discovery": collected > freeze_at,
                "note": "never reconstruct postfreeze information as originally known",
            })
    if errors:
        return {"decision": "BLOCK", "errors": sorted(set(errors)), "gaps": sorted(set(gaps))}

    can_final = (
        len(completed) == 5
        and all((t, day) in daily for t in frozen for day in session_dates)
    )
    if not can_final:
        gaps.append("five-session outcome not fully matured or complete")
    frontier = {
        str(row.get("ticker")).upper() for row in data.get("candidate_packets", [])
        if isinstance(row, dict) and row.get("official_rank") is not None
    }
    if not shadow:
        gaps.append("independent ATR shadow absent")
    elif not can_final:
        gaps.append("ATR shadow comparison forward S5 pending")
    if shadow:
        shadow_ranks = []
        missing_shadow_anchors = []
        for t, row in shadow.items():
            try:
                rank = int(row["rank"])
                shadow_ranks.append(rank)
                price = positive(row["baseline_price"])
                stamp = moment(row["baseline_observed_at_utc"])
                if stamp > freeze_at or abs((freeze_at - stamp).total_seconds()) > 180:
                    missing_shadow_anchors.append(t)
                if t in frozen and abs(price - float(frozen[t]["baseline_price"])) > 1e-8:
                    errors.append(f"{t}: shadow baseline mismatch vs immutable Frozen")
            except (KeyError, ValueError, TypeError):
                missing_shadow_anchors.append(t)
        if sorted(shadow_ranks) != list(range(1, len(shadow) + 1)):
            errors.append("ATR ranks not contiguous")
        if len(shadow) != len(frontier) or shadow.keys() != frontier:
            gaps.append("ATR not scored on exactly same evaluated frontier")
        shadow_top20 = {t for t, row in shadow.items() if str(row.get("rank")) in {str(x) for x in range(1, 21)}}
        if len(shadow_top20) != 20:
            errors.append("ATR Top20 cardinality invalid")
        if missing_shadow_anchors or any(t not in frozen for t in shadow_top20):
            gaps.append("ATR comparison lacks same-cutoff baseline or future bars for nonselected tickers")
        else:
            gaps.append("ATR comparison must still validate independent outcome bars before lift claim")
    if errors:
        return {"decision": "BLOCK", "errors": sorted(set(errors)), "gaps": sorted(set(gaps))}
    known_stage = events[0]["first_known_failure"] if events else UNKNOWN
    if not events and not data["issuer_releases"]:
        gaps.append("missing issuer event evidence: attribution UNKNOWN")
    return {
        "schema": SCHEMA,
        "run_id": run_id,
        "decision": "SHADOW_PARTIAL_NOT_CLEAN" if gaps else "SHADOW_EVIDENCE_READY_NOT_PRODUCTION",
        "maturity": maturity,
        "top20_cumulative_hit10": len(selected_hits),
        "top5_cumulative_hit10": len(top5_set.intersection(selected_hits)),
        "day1_top20_hit10": len(day1_hits),
        "first_known_failure": known_stage,
        "documented_failure_events": events,
        "stale_quote_tickers": sorted(stale),
        "gaps": sorted(set(gaps)),
        "attribution_certainty": "ONLY_VERIFIED_PRIMARY_EVENTS; ALL_OTHER_CAUSES_UNKNOWN",
        "promotion": "DORMANT_SHADOW_TEST_ONLY__NO_PRODUCTION_WEIGHT_CHANGE",
        "original_frozen_mutated": False,
        "full_market_winner_recall": UNKNOWN,
        "model_vs_atr_outperformance": UNKNOWN,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only HASOL temporal replay/attribution shadow")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = audit(json.loads(args.input.read_text(encoding="utf-8")))
    output = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    print(output, end="")
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    return 2 if report["decision"] == "BLOCK" else 0


if __name__ == "__main__":
    sys.exit(main())
