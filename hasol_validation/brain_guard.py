"""Read-only recovery and overdue-review audit of a HASOL Brain snapshot.

No API key, Google credentials or broker actions. The ChatGPT connector reads
the canonical tabs; this pure module audits the supplied arrays. It cannot
retrieve anything by itself and must not be confused with a daemon.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

_EPOCH = date(1899, 12, 30)
_LEGACY = {"MIGRATED_LEGACY_NO_COMMIT_ID", "MIGRATED_COMMITTED"}
_COMMITTED = {"COMMITTED_OFFICIAL", *_LEGACY}


def _as_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdecimal()):
        serial = float(value)
        return _EPOCH + timedelta(days=int(serial)) if serial >= 40000 else None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _num(value: Any) -> float | None:
    try:
        number = float(value)
        return number if number == number and abs(number) != float("inf") else None
    except (TypeError, ValueError):
        return None


def _record(rows: list, key: int) -> dict[str, list]:
    out: dict[str, list] = defaultdict(list)
    for row in rows:
        if len(row) > key and row[key]:
            out[str(row[key])].append(row)
    return out


def audit_brain(snapshot: dict, last_completed_us_session: str) -> dict:
    """Check current state; never modify any source or retroactively fix Frozen."""
    asof = _as_date(last_completed_us_session)
    if asof is None:
        raise ValueError("require independently verified last completed US session")
    for key in ("runs", "frozen", "outcomes", "reviews", "control"):
        if not isinstance(snapshot.get(key), list):
            raise ValueError(f"missing Brain input tab {key}")
    run_rows = [x for x in snapshot["runs"] if x and x[0] and x[0] != "RUN_ID"]
    frozen_rows = [x for x in snapshot["frozen"] if x and x[0] and x[0] != "FROZEN_ID"]
    outcome_rows = [x for x in snapshot["outcomes"] if x and x[0] and x[0] != "OUTCOME_ID"]
    review_rows = [x for x in snapshot["reviews"] if x and x[0] and x[0] != "REVIEW_ID"]
    control = {x[1]: x[2] for x in snapshot["control"] if len(x) > 2 and x[1]}
    runs = _record(run_rows, 0)
    frozens = _record(frozen_rows, 2)
    outcomes = _record(outcome_rows, 1)
    reviews = _record(review_rows, 1)
    errors, warnings, due = [], [], []
    if len(runs) != len(run_rows):
        errors.append("DUPLICATE_RUN_ID")
    if len(set(x[0] for x in frozen_rows)) != len(frozen_rows):
        errors.append("DUPLICATE_FROZEN_ID")
    if len(set(x[0] for x in outcome_rows)) != len(outcome_rows):
        errors.append("DUPLICATE_OUTCOME_ID")
    if len(set(x[0] for x in review_rows)) != len(review_rows):
        errors.append("DUPLICATE_REVIEW_ID")
    for rid, entries in frozens.items():
        if rid not in runs:
            errors.append(f"{rid}:FROZEN_WITHOUT_RUN")
            continue
        run = runs[rid][0]
        ranks = [_num(z[5]) if len(z) > 5 else None for z in entries]
        tops = [z[4] for z in entries if len(z) > 6 and z[6] == "YES"]
        if len(entries) != 20 or sorted(ranks, key=lambda x: x if x is not None else -1) != list(range(1, 21)):
            errors.append(f"{rid}:FROZEN_RANK_20_FAIL")
        if len(tops) != 5 or any(len(z) < 25 or z[24] != "LOCKED" for z in entries):
            errors.append(f"{rid}:FROZEN_LOCK_TOP5_FAIL")
        if any(_num(z[7]) is None or _num(z[7]) <= 0 for z in entries):
            errors.append(f"{rid}:INVALID_FROZEN_BASELINE")
        selected = outcomes.get(rid, [])
        selected = [z for z in selected if len(z) > 6 and str(z[5]).startswith("SELECTED")]
        frozen_by = {z[4]: z for z in entries if len(z) > 7}
        if len(selected) != 20 or len(set(z[3] for z in selected)) != 20:
            errors.append(f"{rid}:SELECTED_OUTCOMES_NOT_20")
        for z in selected:
            f = frozen_by.get(z[3])
            if f is None or _num(z[7]) != _num(f[7]) or _num(z[6]) != _num(f[5]):
                errors.append(f"{rid}:{z[3]}:OUTCOME_BASELINE_RANK_CHANGED")
        session5 = _as_date(run[5]) if len(run) > 5 else None
        if session5 is None:
            warnings.append(f"{rid}:UNKNOWN_S5_DATE")
            continue
        final = [z for z in reviews.get(rid, []) if len(z) > 2 and z[2] == "FINAL"]
        completed = [z for z in selected if len(z) > 10 and z[10] == "FINAL"]
        if session5 <= asof:
            if len(completed) != 20 or len(final) != 1:
                due.append({"run_id": rid, "session5": session5.isoformat(),
                            "final_outcomes_n": len(completed), "final_reviews_n": len(final)})
            elif (sum(z[13] == "HIT" for z in completed) != _num(final[0][5])
                  or sum(z[13] == "HIT" and _num(z[6]) <= 5 for z in completed)
                  != _num(final[0][8])):
                errors.append(f"{rid}:FINAL_REVIEW_COUNTS_MISMATCH")
        elif completed or final:
            errors.append(f"{rid}:FUTURE_S5_MARKED_FINAL")
    for rid, entries in runs.items():
        r = entries[0]
        status = r[16] if len(r) > 16 else ""
        if status in _COMMITTED and rid not in frozens:
            errors.append(f"{rid}:COMMITTED_WITHOUT_FROZEN")
        if "ABORTED" in status and rid in frozens:
            errors.append(f"{rid}:ABORTED_WITH_FROZEN")
    committed = [x for x in run_rows if len(x) > 16 and x[16] in _COMMITTED and x[0] in frozens]
    committed.sort(key=lambda z: str(z[1]) if len(z) > 1 else "")
    newest = committed[-1] if committed else None
    newest_id = newest[0] if newest else None
    if newest_id and control.get("LATEST_FROZEN_RUN_ID") != newest_id:
        warnings.append("CONTROL_LATEST_FROZEN_CACHE_DISAGREES_WITH_RUN_REGISTRY")
    return {
        "status": "FAIL" if errors else "ACTION_REQUIRED" if due else "PASS",
        "last_completed_us_session": asof.isoformat(),
        "run_n": len(run_rows), "frozen_run_n": len(frozens),
        "frozen_n": len(frozen_rows), "outcome_n": len(outcome_rows),
        "review_n": len(review_rows), "latest_frozen_run": newest_id,
        "latest_top5": [z[4] for z in sorted(frozens.get(newest_id, []), key=lambda q: _num(q[5]) or 999)[:5]],
        "clean_forward_n": control.get("CLEAN_FORWARD_RUN_N", "UNKNOWN"),
        "due_final_reviews": due, "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)), "production_writes": 0,
    }
