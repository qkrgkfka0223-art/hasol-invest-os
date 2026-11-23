import copy
import json
import subprocess
import sys

from scripts.audit_matured_backlog import audit


def specimen():
    runs = [{"RUN_ID": f"RUN-{i}", "SESSION5_DATE": date} for i, date in [
        (0, "2026-11-13"), (1, "2026-11-14"), (2, "2026-11-16"), (3, "2026-11-17")
    ]]
    frozen = [{"RUN_ID": f"RUN-{j}", "TICKER_SNAPSHOT": f"T{i:02d}", "LOCK": "LOCKED"}
              for j in range(1, 4) for i in range(20)]
    outcomes = [{"RUN_ID": f"RUN-{j}", "TICKER_SNAPSHOT": f"T{i:02d}",
                 "OUTCOME_STATUS": "FINAL" if j == 1 else "INTERIM"}
                for j in range(1, 4) for i in range(20)]
    reviews = [{"RUN_ID": "RUN-1", "REVIEW_TYPE": "FINAL"}]
    return {"last_completed_us_regular_session": "2026-11-16", "runs": runs,
            "frozen": frozen, "outcomes": outcomes, "reviews": reviews}


def test_detects_overdue_not_just_most_recent():
    s = specimen()
    out = audit(s)
    assert out["decision"] == "OVERDUE_BACKLOG"
    assert out["backlog"] == [{"run_id": "RUN-2", "session5_date": "2026-11-16", "reason": "MISSING_FINAL_AND_UNFINISHED_OUTCOMES", "final_count": 0, "final_outcomes": 0}]
    assert out["completed_run_ids"] == ["RUN-1"]
    assert out["pending"] == [{"run_id": "RUN-3", "session5_date": "2026-11-17"}]
    assert out["no_frozen"] == [{"run_id": "RUN-0", "reason": "NO_ORIGINAL_FROZEN"}]


def test_catches_two_old_overdue_review_runs():
    s = specimen()
    s["runs"][1]["SESSION5_DATE"] = "2026-11-11"
    s["outcomes"] = [dict(x, OUTCOME_STATUS="INTERIM") if x["RUN_ID"] == "RUN-1" else x for x in s["outcomes"]]
    s["reviews"] = []
    out = audit(s)
    assert [b["run_id"] for b in out["backlog"]] == ["RUN-1", "RUN-2"]


def test_all_matured_complete_is_idempotent():
    s = specimen()
    s["reviews"].append({"RUN_ID": "RUN-2", "REVIEW_TYPE": "FINAL"})
    s["outcomes"] = [dict(x, OUTCOME_STATUS="FINAL") if x["RUN_ID"] == "RUN-2" else x for x in s["outcomes"]]
    for i in range(2):
        assert audit(s)["decision"] == "NO_OVERDUE"


def test_final_review_without_20_final_outcomes_remains_backlog():
    s = specimen()
    s["reviews"].append({"RUN_ID": "RUN-2", "REVIEW_TYPE": "FINAL"})
    out = audit(s)
    assert out["decision"] == "OVERDUE_BACKLOG"
    assert out["backlog"][0]["reason"] == "FINAL_WITH_NONFINAL_OUTCOMES"


def test_final_duplicate_is_invalid():
    s = specimen()
    s["reviews"].extend([{"RUN_ID": "RUN-1", "REVIEW_TYPE": "FINAL"}])
    out = audit(s)
    assert out["decision"] == "INVALID_INPUT"
    assert "duplicated FINAL" in out["errors"][0]


def test_missing_outcome_or_mismatched_ticker_is_invalid():
    s = specimen()
    s["outcomes"] = [x for x in s["outcomes"] if not (x["RUN_ID"] == "RUN-2" and x["TICKER_SNAPSHOT"] == "T01")]
    out = audit(s)
    assert out["decision"] == "INVALID_INPUT"
    assert any("Outcomes" in e for e in out["errors"])


def test_unlocked_frozen_invalid():
    s = specimen()
    s["frozen"][0]["LOCK"] = "OPEN"
    out = audit(s)
    assert out["decision"] == "INVALID_INPUT"
    assert any("locked" in e for e in out["errors"])


def test_duplicate_registered_run_invalid():
    s = specimen()
    s["runs"].append(copy.deepcopy(s["runs"][0]))
    assert audit(s)["decision"] == "INVALID_INPUT"


def test_cli_exit_codes(tmp_path):
    raw = tmp_path / "snapshot.json"
    cmd = [sys.executable, "-m", "scripts.audit_matured_backlog", "--input", str(raw)]
    raw.write_text(json.dumps(specimen()))
    bad = subprocess.run(cmd, capture_output=True, text=True)
    assert bad.returncode == 2
    valid = specimen()
    valid["reviews"].append({"RUN_ID": "RUN-2", "REVIEW_TYPE": "FINAL"})
    valid["outcomes"] = [dict(x, OUTCOME_STATUS="FINAL") if x["RUN_ID"] == "RUN-2" else x for x in valid["outcomes"]]
    raw.write_text(json.dumps(valid))
    good = subprocess.run(cmd, capture_output=True, text=True)
    assert good.returncode == 0


def test_reject_invalid_session_date():
    s = specimen()
    s["last_completed_us_regular_session"] = "2026-11-31"
    assert audit(s)["decision"] == "INVALID_INPUT"
