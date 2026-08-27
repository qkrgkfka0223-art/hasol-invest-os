from __future__ import annotations

import json
from pathlib import Path

from hasol_detector.web_event_model import normalize_payload

DATES = ["2026-08-24", "2026-08-25", "2026-08-26"]


def test_three_consecutive_e2e_fixtures_are_future_blocked_and_restored():
    expected_restore = ["BASELINE_V3", "E2E-20260824-GROWTH", "E2E-20260825-GROWTH"]
    for day, restore in zip(DATES, expected_restore):
        raw = json.loads(Path(f"runtime/e2e/{day}.json").read_text(encoding="utf-8"))
        assert raw["restore_from"] == restore
        out = normalize_payload(raw)
        assert out["run_type"] == "E2E_SIM"
        assert out["eligible_for_prediction"] is True
        assert out["prediction_date_et"] == day
        assert out["candidate_count"] == 5
        assert out["event_count_raw"] == out["event_count_deduped"] == 5
        assert all(row["official_verified"] for row in out["candidates"])


def test_e2e_cutoff_is_exactly_0925_et():
    for day in DATES:
        raw = json.loads(Path(f"runtime/e2e/{day}.json").read_text(encoding="utf-8"))
        assert raw["cutoff_et"].endswith("T09:25:00-04:00")
