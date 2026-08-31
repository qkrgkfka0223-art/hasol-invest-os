from __future__ import annotations

import json

import pytest

from scripts.build_live_candidate_snapshot import (
    DECISION_SCHEMA,
    EVENT_SCHEMA,
    MATERIALITY_DROP,
    MATERIALITY_KEEP,
    SESSION_SCHEMA,
    build_snapshot,
)

DATE = "2026-08-31"


def _session():
    return {
        "session_schema": SESSION_SCHEMA,
        "prediction_date_et": DATE,
        "run_type": "PREMARKET",
        "eligible_for_prediction": True,
        "as_of_utc": "2026-08-31T13:15:00Z",
        "cutoff_et": "2026-08-31T09:25:00-04:00",
    }


def _event(ticker="ABC", event_id="ABC-E1"):
    return {
        "ticker": ticker,
        "event_id": event_id,
        "event_type": "GUIDANCE",
        "axis": "EARNINGS_REVISION",
        "event_published_at_utc": "2026-08-31T12:00:00Z",
        "headline": f"{ticker} raises guidance",
        "flow_path": "raised guidance -> estimate revisions -> capital inflow",
        "official_verified": True,
        "official_source_url": f"https://investor.example.com/{ticker.lower()}/release",
    }


def _write_event(root, *, ticker="ABC", event_id="ABC-E1"):
    target = root / DATE
    target.mkdir(parents=True, exist_ok=True)
    payload = {
        "ledger_schema": EVENT_SCHEMA,
        "prediction_date_et": DATE,
        "run_type": "PREMARKET",
        "event": _event(ticker, event_id),
    }
    (target / f"{event_id}.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_decision(root, *, decision_id, event_id="ABC-E1", action=MATERIALITY_DROP, decided_at="2026-08-31T13:00:00Z", reason="stale carryover", target_date=DATE):
    target = root / DATE
    target.mkdir(parents=True, exist_ok=True)
    payload = {
        "decision_schema": DECISION_SCHEMA,
        "decision_id": decision_id,
        "prediction_date_et": target_date,
        "run_type": "PREMARKET",
        "event_id": event_id,
        "action": action,
        "decided_at_utc": decided_at,
    }
    if reason is not None:
        payload["reason"] = reason
    (target / f"{decision_id}.json").write_text(json.dumps(payload), encoding="utf-8")


def _build(tmp_path):
    session_path = tmp_path / "session.json"
    session_path.write_text(json.dumps(_session()), encoding="utf-8")
    output = tmp_path / "effective.json"
    manifest_path = tmp_path / "manifest.json"
    manifest = build_snapshot(
        session_path,
        tmp_path / "events",
        tmp_path / "intraday",
        output,
        manifest_path,
        tmp_path / "decisions",
    )
    return json.loads(output.read_text(encoding="utf-8")), manifest


def test_materiality_drop_excludes_event_but_preserves_audit_record(tmp_path):
    _write_event(tmp_path / "events")
    _write_decision(tmp_path / "decisions", decision_id="DROP-1")

    payload, manifest = _build(tmp_path)

    assert payload["candidates"] == []
    assert manifest["event_file_count"] == 1
    assert manifest["active_event_file_count"] == 0
    assert manifest["decision_file_count"] == 1
    assert manifest["excluded_event_ids"] == ["ABC-E1"]
    assert manifest["event_files"][0]["active"] is False
    assert manifest["latest_materiality_decisions"][0]["action"] == MATERIALITY_DROP


def test_later_keep_reactivates_previously_dropped_event(tmp_path):
    _write_event(tmp_path / "events")
    _write_decision(tmp_path / "decisions", decision_id="DROP-1", decided_at="2026-08-31T13:00:00Z")
    _write_decision(
        tmp_path / "decisions",
        decision_id="KEEP-2",
        action=MATERIALITY_KEEP,
        decided_at="2026-08-31T13:05:00Z",
        reason="materiality restored",
    )

    payload, manifest = _build(tmp_path)

    assert [row["ticker"] for row in payload["candidates"]] == ["ABC"]
    assert manifest["active_event_file_count"] == 1
    assert manifest["excluded_event_ids"] == []
    assert manifest["decision_file_count"] == 2
    assert manifest["latest_materiality_decisions"][0]["action"] == MATERIALITY_KEEP


def test_materiality_decision_target_date_mismatch_is_rejected(tmp_path):
    _write_event(tmp_path / "events")
    _write_decision(tmp_path / "decisions", decision_id="DROP-1", target_date="2026-08-30")
    source = tmp_path / "decisions" / DATE / "DROP-1.json"
    raw = json.loads(source.read_text(encoding="utf-8"))
    raw["prediction_date_et"] = "2026-08-30"
    source.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ValueError, match="decision target date mismatch"):
        _build(tmp_path)


def test_materiality_drop_requires_reason(tmp_path):
    _write_event(tmp_path / "events")
    _write_decision(tmp_path / "decisions", decision_id="DROP-1", reason=None)

    with pytest.raises(ValueError, match="MATERIALITY_DROP reason"):
        _build(tmp_path)
