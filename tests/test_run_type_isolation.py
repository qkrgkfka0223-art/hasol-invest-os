from __future__ import annotations

import json

from scripts.build_live_candidate_snapshot import DECISION_SCHEMA, EVENT_SCHEMA, SESSION_SCHEMA, build_snapshot
from scripts.validate_live_state_asof import validate_state_asof

DATE = "2026-09-01"


def _write_session(path, *, run_type: str, eligible: bool, as_of: str) -> None:
    path.write_text(
        json.dumps(
            {
                "session_schema": SESSION_SCHEMA,
                "prediction_date_et": DATE,
                "run_type": run_type,
                "eligible_for_prediction": eligible,
                "as_of_utc": as_of,
                "cutoff_et": "2026-09-01T09:30:00-04:00",
            }
        ),
        encoding="utf-8",
    )


def _write_event(root, *, run_type: str, ticker: str, event_id: str, published: str) -> None:
    target = root / DATE
    target.mkdir(parents=True, exist_ok=True)
    payload = {
        "ledger_schema": EVENT_SCHEMA,
        "prediction_date_et": DATE,
        "run_type": run_type,
        "recorded_at_utc": published,
        "event": {
            "ticker": ticker,
            "event_id": event_id,
            "event_type": "GUIDANCE",
            "axis": "EARNINGS_REVISION",
            "event_published_at_utc": published,
            "headline": f"{ticker} event",
            "flow_path": "event -> estimate revision -> capital flow",
            "official_verified": True,
            "official_source_url": f"https://example.com/{ticker}",
        },
    }
    (target / f"{event_id}.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_decision(root, *, run_type: str, decision_id: str, event_id: str, decided_at: str) -> None:
    target = root / DATE
    target.mkdir(parents=True, exist_ok=True)
    payload = {
        "decision_schema": DECISION_SCHEMA,
        "decision_id": decision_id,
        "prediction_date_et": DATE,
        "run_type": run_type,
        "event_id": event_id,
        "action": "MATERIALITY_DROP",
        "reason": "test decision",
        "decided_at_utc": decided_at,
    }
    (target / f"{decision_id}.json").write_text(json.dumps(payload), encoding="utf-8")


def test_intraday_snapshot_ignores_premarket_decision_in_shared_ledger(tmp_path):
    session_path = tmp_path / "session.json"
    _write_session(session_path, run_type="INTRADAY_EVENT", eligible=False, as_of="2026-09-01T14:10:00Z")
    _write_event(
        tmp_path / "intraday",
        run_type="INTRADAY_EVENT",
        ticker="XYZ",
        event_id="XYZ-INT",
        published="2026-09-01T14:00:00Z",
    )
    _write_decision(
        tmp_path / "decisions",
        run_type="PREMARKET",
        decision_id="DROP-ABC-PRE",
        event_id="ABC-PRE",
        decided_at="2026-09-01T12:00:00Z",
    )

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
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert [row["ticker"] for row in payload["candidates"]] == ["XYZ"]
    assert manifest["decision_file_count_total"] == 1
    assert manifest["decision_file_count"] == 0
    assert manifest["ignored_cross_run_type_decision_count"] == 1
    assert manifest["ignored_cross_run_type_decisions"][0]["decision_id"] == "DROP-ABC-PRE"

    report = validate_state_asof(
        session_path,
        output,
        tmp_path / "events",
        tmp_path / "intraday",
        tmp_path / "decisions",
    )
    assert report["valid"] is True
    assert report["decision_file_count_total"] == 1
    assert report["decision_file_count"] == 0
    assert report["ignored_cross_run_type_decision_count"] == 1


def test_premarket_snapshot_ignores_intraday_decision_in_shared_ledger(tmp_path):
    session_path = tmp_path / "session.json"
    _write_session(session_path, run_type="PREMARKET", eligible=True, as_of="2026-09-01T13:20:00Z")
    _write_event(
        tmp_path / "events",
        run_type="PREMARKET",
        ticker="ABC",
        event_id="ABC-PRE",
        published="2026-09-01T12:00:00Z",
    )
    _write_decision(
        tmp_path / "decisions",
        run_type="INTRADAY_EVENT",
        decision_id="DROP-XYZ-INT",
        event_id="XYZ-INT",
        decided_at="2026-09-01T14:05:00Z",
    )

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
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert [row["ticker"] for row in payload["candidates"]] == ["ABC"]
    assert manifest["decision_file_count"] == 0
    assert manifest["ignored_cross_run_type_decision_count"] == 1
