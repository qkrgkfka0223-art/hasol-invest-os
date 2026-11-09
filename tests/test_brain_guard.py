from __future__ import annotations

from copy import deepcopy
from hasol_validation.brain_guard import audit_brain


def _run(rid, start, end, created, *, state="COMMITTED_OFFICIAL"):
    z = [""] * 30
    z[0], z[1], z[4], z[5], z[16] = rid, created, start, end, state
    return z


def _frozen(rid, ticker, rank):
    x = [""] * 25
    x[0], x[2], x[4], x[5], x[6] = f"{rid}|{ticker}|{rank}", rid, ticker, rank, "YES" if rank <= 5 else "NO"
    x[7], x[24] = float(rank + 10), "LOCKED"
    return x


def _outcome(rid, ticker, rank, *, final, legacy_scope=False):
    x = [""] * 39
    x[0], x[1], x[3] = f"{rid}|{ticker}|PRODUCTION", rid, ticker
    x[5] = "EVALUATED" if legacy_scope else "SELECTED_FROZEN"
    x[6], x[7] = rank, float(rank + 10)
    x[10] = "FINAL" if final else "PENDING_S1_S5"
    x[13] = "HIT" if final and rank <= 3 else "MISS" if final else "PENDING"
    return x


def _review(rid):
    x = [""] * 50
    x[0], x[1], x[2] = f"REVIEW|{rid}|FINAL", rid, "FINAL"
    x[5], x[8] = 3, 3
    return x


def _snapshot():
    old, new = "RUN-LEGACY", "RUN-NEW"
    return {
        "runs": [
            _run(old, "2026-11-02", "46332", "2026-11-02T12:00:00Z", state="MIGRATED_COMMITTED"),
            _run(new, "2026-11-06", "2026-11-12", "2026-11-06T12:00:00Z"),
        ],
        "frozen": [
            *[_frozen(old, f"A{i:02d}", i) for i in range(1, 21)],
            *[_frozen(new, f"N{i:02d}", i) for i in range(1, 21)],
        ],
        "outcomes": [
            *[_outcome(old, f"A{i:02d}", i, final=True, legacy_scope=True) for i in range(1, 21)],
            *[_outcome(new, f"N{i:02d}", i, final=False) for i in range(1, 21)],
        ],
        "reviews": [_review(old)],
        "control": [["", "LATEST_FROZEN_RUN_ID", new],
                    ["", "CLEAN_FORWARD_RUN_N", "0"]],
    }


def test_restore_two_runs_with_legacy_serial_date_and_correct_final():
    result = audit_brain(_snapshot(), "2026-11-06")
    assert result["status"] == "PASS"
    assert result["latest_frozen_run"] == "RUN-NEW"
    assert result["latest_top5"] == [f"N{i:02d}" for i in range(1, 6)]
    assert result["frozen_n"] == 40
    assert result["frozen_run_n"] == 2
    assert result["due_final_reviews"] == []
    assert "RUN-LEGACY:LEGACY_EVALUATED_SCOPE_RECONCILED_TO_FROZEN" in result["warnings"]
    assert result["production_writes"] == 0
    assert result["clean_forward_n"] == "0"


def test_after_s5_missing_final_is_action_required_without_rewriting_frozen():
    raw = _snapshot()
    before = deepcopy(raw["frozen"])
    x = audit_brain(raw, "2026-11-13")
    assert x["status"] == "ACTION_REQUIRED"
    assert x["due_final_reviews"] == [{
        "run_id": "RUN-NEW", "session5": "2026-11-12",
        "final_outcomes_n": 0, "final_reviews_n": 0,
    }]
    assert raw["frozen"] == before


def test_one_missing_outcome_is_detected():
    raw = _snapshot()
    raw["outcomes"].pop()
    x = audit_brain(raw, "2026-11-06")
    assert x["status"] == "FAIL"
    assert "RUN-NEW:SELECTED_OUTCOMES_NOT_20" in x["errors"]


def test_wrong_baseline_detected_even_with_matching_symbols():
    raw = _snapshot()
    raw["outcomes"][0][7] += 1.0
    x = audit_brain(raw, "2026-11-06")
    assert x["status"] == "FAIL"
    assert "RUN-LEGACY:A01:OUTCOME_BASELINE_RANK_CHANGED" in x["errors"]


def test_top5_or_frozen_rank_corruption_detected():
    raw = _snapshot()
    raw["frozen"][0][6] = "NO"
    raw["frozen"][1][5] = 1
    x = audit_brain(raw, "2026-11-06")
    assert x["status"] == "FAIL"
    assert "RUN-LEGACY:FROZEN_RANK_20_FAIL" in x["errors"]
    assert "RUN-LEGACY:FROZEN_LOCK_TOP5_FAIL" in x["errors"]


def test_wrong_final_hit_count_detected():
    raw = _snapshot()
    raw["reviews"][0][5] = 20
    x = audit_brain(raw, "2026-11-06")
    assert x["status"] == "FAIL"
    assert "RUN-LEGACY:FINAL_REVIEW_COUNTS_MISMATCH" in x["errors"]


def test_aborted_run_must_not_have_frozen():
    raw = _snapshot()
    raw["runs"][1][16] = "ABORTED"
    x = audit_brain(raw, "2026-11-06")
    assert x["status"] == "FAIL"
    assert "RUN-NEW:ABORTED_WITH_FROZEN" in x["errors"]


def test_final_review_before_fifth_session_rejected():
    raw = _snapshot()
    raw["outcomes"][20:40] = [
        _outcome("RUN-NEW", f"N{i:02d}", i, final=True) for i in range(1, 21)
    ]
    raw["reviews"].append(_review("RUN-NEW"))
    x = audit_brain(raw, "2026-11-06")
    assert x["status"] == "FAIL"
    assert "RUN-NEW:FUTURE_S5_MARKED_FINAL" in x["errors"]


def test_cache_disagreement_warns_but_registry_is_authority():
    raw = _snapshot()
    raw["control"][0][2] = "RUN-LEGACY"
    x = audit_brain(raw, "2026-11-06")
    assert x["latest_frozen_run"] == "RUN-NEW"
    assert "CONTROL_LATEST_FROZEN_CACHE_DISAGREES_WITH_RUN_REGISTRY" in x["warnings"]


def test_duplicate_outcome_row_detected():
    raw = _snapshot()
    raw["outcomes"].append(deepcopy(raw["outcomes"][0]))
    x = audit_brain(raw, "2026-11-06")
    assert x["status"] == "FAIL"
    assert "DUPLICATE_OUTCOME_ID" in x["errors"]
