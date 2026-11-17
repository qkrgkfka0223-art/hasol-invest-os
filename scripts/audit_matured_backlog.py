"""Deterministic, read-only audit of overdue HASOL five-session FINAL reviews.

Required input is a same-time read of 01_RUNS, 03_FROZEN, 04_OUTCOMES,
05_REVIEWS, plus the LAST COMPLETED US REGULAR SESSION from a market calendar.
Never infers schedule execution from missing journal alone. Never writes Sheets.
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path


def _date(value):
    if not isinstance(value, str):
        raise ValueError("date must be YYYY-MM-DD")
    d = date.fromisoformat(value)
    if d.isoformat() != value:
        raise ValueError("date must be YYYY-MM-DD")
    return d


def audit(snapshot):
    errors, backlog, complete, pending, skipped = [], [], [], [], []
    if not isinstance(snapshot, dict):
        return {"decision": "INVALID_INPUT", "errors": ["root must be object"]}
    try:
        cutoff = _date(snapshot["last_completed_us_regular_session"])
    except (KeyError, ValueError, TypeError) as exc:
        return {"decision": "INVALID_INPUT", "errors": [f"invalid last completed session: {exc}"]}
    arrays = ["runs", "frozen", "outcomes", "reviews"]
    if any(not isinstance(snapshot.get(k), list) for k in arrays):
        return {"decision": "INVALID_INPUT", "errors": ["runs/frozen/outcomes/reviews must be arrays"]}

    frozen = defaultdict(list)
    outcomes = defaultdict(list)
    reviews = defaultdict(list)
    for key, dst in [("frozen", frozen), ("outcomes", outcomes), ("reviews", reviews)]:
        for n, row in enumerate(snapshot[key]):
            if not isinstance(row, dict) or not str(row.get("RUN_ID") or "").strip():
                errors.append(f"{key}[{n}] missing RUN_ID")
                continue
            dst[row["RUN_ID"]].append(row)
    run_ids = []
    for i, run in enumerate(snapshot["runs"]):
        if not isinstance(run, dict) or not str(run.get("RUN_ID") or "").strip():
            errors.append(f"runs[{i}] missing RUN_ID")
            continue
        rid = run["RUN_ID"]
        run_ids.append(rid)
        fr = frozen.get(rid, [])
        if len(fr) == 0:
            skipped.append({"run_id": rid, "reason": "NO_ORIGINAL_FROZEN"})
            continue
        if len(fr) != 20 or len({f.get("TICKER_SNAPSHOT") for f in fr}) != 20:
            errors.append(f"{rid}: original Frozen must be 20 unique tickers")
            continue
        if any(f.get("LOCK") != "LOCKED" for f in fr):
            errors.append(f"{rid}: original Frozen not fully locked")
            continue
        try:
            due = _date(run["SESSION5_DATE"])
        except (KeyError, ValueError, TypeError) as exc:
            errors.append(f"{rid}: invalid SESSION5_DATE: {exc}")
            continue
        if due > cutoff:
            pending.append({"run_id": rid, "session5_date": str(due)})
            continue
        finals = [r for r in reviews.get(rid, []) if r.get("REVIEW_TYPE") == "FINAL"]
        oo = outcomes.get(rid, [])
        old_names = {x["TICKER_SNAPSHOT"] for x in fr}
        out_names = [x.get("TICKER_SNAPSHOT") for x in oo]
        valid_outcomes = len(oo) == 20 and len(set(out_names)) == 20 and set(out_names) == old_names
        if len(finals) > 1:
            errors.append(f"{rid}: duplicated FINAL reviews ({len(finals)})")
            continue
        if not valid_outcomes:
            errors.append(f"{rid}: missing/duplicated/mismatched 20 Outcomes")
            continue
        finalized_outcomes = all(o.get("OUTCOME_STATUS") == "FINAL" for o in oo)
        if len(finals) == 1 and finalized_outcomes:
            complete.append(rid)
        else:
            reason = ("NO_FINAL" if not finals else "FINAL_WITH_NONFINAL_OUTCOMES")
            if not finalized_outcomes and not finals:
                reason = "MISSING_FINAL_AND_UNFINISHED_OUTCOMES"
            backlog.append({"run_id": rid, "session5_date": str(due), "reason": reason, "final_count": len(finals), "final_outcomes": sum(o.get("OUTCOME_STATUS") == "FINAL" for o in oo)})
    duplicates = [rid for rid, n in Counter(run_ids).items() if n > 1]
    if duplicates:
        errors.extend(f"{rid}: duplicated RUN_ID in registry" for rid in duplicates)
    for k, dst in [("frozen", frozen), ("outcomes", outcomes), ("reviews", reviews)]:
        for rid in dst:
            if rid not in set(run_ids):
                errors.append(f"{k}: orphan RUN_ID {rid}")
    backlog.sort(key=lambda x: (x["session5_date"], x["run_id"]))
    pending.sort(key=lambda x: (x["session5_date"], x["run_id"]))
    decision = "INVALID_INPUT" if errors else ("OVERDUE_BACKLOG" if backlog else "NO_OVERDUE")
    return {
        "decision": decision,
        "last_completed_us_regular_session": str(cutoff),
        "backlog": backlog,
        "completed_run_ids": sorted(complete),
        "pending": pending,
        "no_frozen": sorted(skipped, key=lambda x: x["run_id"]),
        "errors": sorted(set(errors)),
        "metrics": {"overdue": len(backlog), "complete": len(complete), "pending": len(pending), "unfrozen": len(skipped)},
        "note": "Input-only audit; independently verify current US session date and Sheet values. Does not assert scheduled execution occurred.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Find every missing matured HASOL FINAL from current Brain snapshot")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = audit(json.loads(args.input.read_text(encoding="utf-8")))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"decision": "INVALID_INPUT", "errors": [str(exc)]}), file=sys.stderr)
        return 3
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return {"NO_OVERDUE": 0, "OVERDUE_BACKLOG": 2, "INVALID_INPUT": 3}[result["decision"]]


if __name__ == "__main__":
    sys.exit(main())
