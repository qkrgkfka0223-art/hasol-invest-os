from __future__ import annotations

import json

import pytest

from scripts.build_live_candidate_snapshot import EVENT_SCHEMA, SESSION_SCHEMA, build_snapshot
from scripts.validate_live_state_asof import validate_state_asof


def _session(*, run_type="PREMARKET", as_of="2026-09-01T13:20:00Z", cutoff="2026-09-01T09:30:00-04:00", eligible=True):
    return {
        "session_schema": SESSION_SCHEMA,
        "prediction_date_et": "2026-09-01",
        "run_type": run_type,
        "eligible_for_prediction": eligible,
        "as_of_utc": as_of,
        "cutoff_et": cutoff,
    }


def _event(event_id: str, ticker: str, published: str):
    return {
        "ticker": ticker,
        "event_id": event_id,
        "event_type": "GUIDANCE",
        "axis": "EARNINGS_REVISION",
        "event_published_at_utc": published,
        "headline": f"{ticker} raises guidance",
        "flow_path": "guidance -> revisions -> capital flow",
        "official_verified": True,
        "official_source_url": f"https://example.com/{ticker}",
    }


def _write_event(root, *, run_type, event_id="ABC-E1", ticker="ABC", published="2026-09-01T12:00:00Z", recorded="2026-09-01T12:01:00Z"):
    target = root / "2026-09-01"
    target.mkdir(parents=True, exist_ok=True)
    wrapper = {
        "ledger_schema": EVENT_SCHEMA,
        "prediction_date_et": "2026-09-01",
        "run_type": run_type,
        "recorded_at_utc": recorded,
        "event": _event(event_id, ticker, published),
    }
    (target / f"{event_id}.json").write_text(json.dumps(wrapper), encoding="utf-8")


def _build(tmp_path, session):
    session_path = tmp_path / "session.json"
    session_path.write_text(json.dumps(session), encoding="utf-8")
    premarket = tmp_path / "events"
    intraday = tmp_path / "intraday"
    decisions = tmp_path / "decisions"
    output = tmp_path / "effective.json"
    manifest_path = tmp_path / "manifest.json"
    return session_path, premarket, intraday, decisions, output, manifest_path


def test_legacy_intraday_alias_is_canonicalized_instead_of_crashing(tmp_path):
    session_path, premarket, intraday, decisions, output, manifest_path = _build(
        tmp_path, _session(run_type="INTRADAY", eligible=False)
    )
    _write_event(intraday, run_type="INTRADAY", published="2026-09-01T12:00:00Z")

    manifest = build_snapshot(session_path, premarket, intraday, output, manifest_path, decisions)
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["run_type"] == "INTRADAY_EVENT"
    assert manifest["run_type"] == "INTRADAY_EVENT"
    assert manifest["run_type_canonicalized"] is True


def test_premarket_event_after_regular_open_barrier_is_rejected(tmp_path):
    session_path, premarket, intraday, decisions, output, manifest_path = _build(
        tmp_path, _session(as_of="2026-09-01T14:00:00Z")
    )
    _write_event(
        premarket,
        run_type="PREMARKET",
        published="2026-09-01T13:31:00Z",
        recorded="2026-09-01T13:32:00Z",
    )

    with pytest.raises(ValueError, match="after prediction information barrier"):
        build_snapshot(session_path, premarket, intraday, output, manifest_path, decisions)


def test_event_newer_than_session_asof_is_rejected(tmp_path):
    session_path, premarket, intraday, decisions, output, manifest_path = _build(
        tmp_path, _session(as_of="2026-09-01T12:30:00Z")
    )
    _write_event(
        premarket,
        run_type="PREMARKET",
        published="2026-09-01T12:31:00Z",
        recorded="2026-09-01T12:32:00Z",
    )

    with pytest.raises(ValueError, match="newer than session as_of_utc"):
        build_snapshot(session_path, premarket, intraday, output, manifest_path, decisions)


def test_validator_rejects_future_published_event_even_if_effective_file_exists(tmp_path):
    session_path, premarket, intraday, decisions, output, manifest_path = _build(
        tmp_path, _session(as_of="2026-09-01T12:30:00Z")
    )
    _write_event(
        premarket,
        run_type="PREMARKET",
        published="2026-09-01T12:31:00Z",
        recorded="2026-09-01T12:29:00Z",
    )
    output.write_text(
        json.dumps({
            "run_type": "PREMARKET",
            "as_of_utc": "2026-09-01T12:30:00Z",
        }),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="predates event publication"):
        validate_state_asof(session_path, output, premarket, intraday, decisions)


def test_validator_accepts_legacy_intraday_alias_and_reports_canonical_type(tmp_path):
    session_path, premarket, intraday, decisions, output, manifest_path = _build(
        tmp_path, _session(run_type="INTRADAY", eligible=False)
    )
    _write_event(intraday, run_type="INTRADAY", published="2026-09-01T12:00:00Z")
    build_snapshot(session_path, premarket, intraday, output, manifest_path, decisions)

    report = validate_state_asof(session_path, output, premarket, intraday, decisions)
    assert report["valid"] is True
    assert report["run_type"] == "INTRADAY_EVENT"
    assert report["run_type_canonicalized"] is True
