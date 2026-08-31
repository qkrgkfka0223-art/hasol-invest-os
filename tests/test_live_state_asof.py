import json
from pathlib import Path

import pytest

from scripts.validate_live_state_asof import validate_state_asof


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _session(as_of: str) -> dict:
    return {
        "session_schema": "HASOL-WEB-SESSION-v1",
        "prediction_date_et": "2026-08-31",
        "run_type": "PREMARKET",
        "eligible_for_prediction": True,
        "as_of_utc": as_of,
        "cutoff_et": "2026-08-31T09:25:00-04:00",
    }


def _decision(decided_at: str) -> dict:
    return {
        "decision_schema": "HASOL-WEB-DECISION-v1",
        "decision_id": "DEC-1",
        "prediction_date_et": "2026-08-31",
        "run_type": "PREMARKET",
        "event_id": "AAA-1",
        "action": "MATERIALITY_DROP",
        "decided_at_utc": decided_at,
        "reason": "test",
    }


def test_rejects_stale_session_asof_before_applicable_decision(tmp_path: Path):
    session = tmp_path / "session.json"
    effective = tmp_path / "effective.json"
    decisions = tmp_path / "decisions"
    _write(session, _session("2026-08-31T01:40:00Z"))
    _write(effective, {"as_of_utc": "2026-08-31T01:40:00Z"})
    _write(decisions / "2026-08-31" / "d.json", _decision("2026-08-31T06:29:00Z"))

    with pytest.raises(ValueError, match="predates an applicable materiality decision"):
        validate_state_asof(session, effective, tmp_path / "events", tmp_path / "intraday", decisions)


def test_accepts_session_asof_covering_decision_state(tmp_path: Path):
    session = tmp_path / "session.json"
    effective = tmp_path / "effective.json"
    decisions = tmp_path / "decisions"
    _write(session, _session("2026-08-31T06:30:00Z"))
    _write(effective, {"as_of_utc": "2026-08-31T06:30:00Z"})
    _write(decisions / "2026-08-31" / "d.json", _decision("2026-08-31T06:29:00Z"))

    report = validate_state_asof(session, effective, tmp_path / "events", tmp_path / "intraday", decisions)
    assert report["valid"] is True
    assert report["max_applicable_decision_at_utc"] == "2026-08-31T06:29:00Z"


def test_post_cutoff_decision_is_audit_only_for_asof_gate(tmp_path: Path):
    session = tmp_path / "session.json"
    effective = tmp_path / "effective.json"
    decisions = tmp_path / "decisions"
    _write(session, _session("2026-08-31T06:30:00Z"))
    _write(effective, {"as_of_utc": "2026-08-31T06:30:00Z"})
    _write(decisions / "2026-08-31" / "d.json", _decision("2026-08-31T14:00:00Z"))

    report = validate_state_asof(session, effective, tmp_path / "events", tmp_path / "intraday", decisions)
    assert report["applicable_decision_count"] == 0
    assert report["ignored_post_cutoff_decision_ids"] == ["DEC-1"]


def test_rejects_event_recorded_after_session_asof(tmp_path: Path):
    session = tmp_path / "session.json"
    effective = tmp_path / "effective.json"
    events = tmp_path / "events"
    _write(session, _session("2026-08-31T06:30:00Z"))
    _write(effective, {"as_of_utc": "2026-08-31T06:30:00Z"})
    _write(
        events / "2026-08-31" / "e.json",
        {
            "ledger_schema": "HASOL-WEB-EVENT-v1",
            "prediction_date_et": "2026-08-31",
            "run_type": "PREMARKET",
            "recorded_at_utc": "2026-08-31T06:31:00Z",
            "event": {"ticker": "AAA", "event_id": "AAA-1"},
        },
    )

    with pytest.raises(ValueError, match="predates recorded event state"):
        validate_state_asof(session, effective, events, tmp_path / "intraday", tmp_path / "decisions")
