from __future__ import annotations

import json

import pytest

from scripts.build_live_candidate_snapshot import EVENT_SCHEMA, SESSION_SCHEMA, build_snapshot


def _session(*, run_type="PREMARKET", eligible=True):
    return {
        "session_schema": SESSION_SCHEMA,
        "prediction_date_et": "2026-08-31",
        "run_type": run_type,
        "eligible_for_prediction": eligible,
        "as_of_utc": "2026-08-31T13:20:00Z",
        "cutoff_et": "2026-08-31T09:25:00-04:00",
    }


def _event(ticker: str, published: str):
    return {
        "ticker": ticker,
        "event_id": f"{ticker}-E1",
        "event_type": "GUIDANCE",
        "axis": "EARNINGS_REVISION",
        "event_published_at_utc": published,
        "headline": f"{ticker} raises guidance",
        "flow_path": "raised guidance -> estimate revisions -> capital inflow",
        "official_verified": True,
        "official_source_url": f"https://investor.example.com/{ticker.lower()}/release",
    }


def _write_event(root, ticker: str, published: str, *, run_type="PREMARKET", target_date="2026-08-31"):
    target = root / target_date
    target.mkdir(parents=True, exist_ok=True)
    envelope = {
        "ledger_schema": EVENT_SCHEMA,
        "prediction_date_et": target_date,
        "run_type": run_type,
        "event": _event(ticker, published),
    }
    (target / f"{ticker}-E1.json").write_text(json.dumps(envelope), encoding="utf-8")


def test_premarket_ledger_builds_deterministic_snapshot(tmp_path):
    session_path = tmp_path / "session.json"
    session_path.write_text(json.dumps(_session()), encoding="utf-8")
    premarket_root = tmp_path / "events"
    intraday_root = tmp_path / "intraday"
    _write_event(premarket_root, "XYZ", "2026-08-31T12:00:00Z")
    _write_event(premarket_root, "ABC", "2026-08-31T11:30:00Z")

    output = tmp_path / "effective.json"
    manifest_path = tmp_path / "manifest.json"
    manifest = build_snapshot(session_path, premarket_root, intraday_root, output, manifest_path)
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert [row["ticker"] for row in payload["candidates"]] == ["ABC", "XYZ"]
    assert manifest["event_file_count"] == 2
    assert manifest["event_count_deduped"] == 2
    assert manifest["candidate_count"] == 2
    assert len(manifest["snapshot_input_sha256"]) == 64


def test_intraday_after_cutoff_is_valid_append_only_observation(tmp_path):
    session_path = tmp_path / "session.json"
    session_path.write_text(json.dumps(_session(run_type="INTRADAY_EVENT", eligible=False)), encoding="utf-8")
    premarket_root = tmp_path / "events"
    intraday_root = tmp_path / "intraday"
    _write_event(
        intraday_root,
        "ROIV",
        "2026-08-31T15:00:00Z",
        run_type="INTRADAY_EVENT",
    )

    output = tmp_path / "effective.json"
    manifest_path = tmp_path / "manifest.json"
    manifest = build_snapshot(session_path, premarket_root, intraday_root, output, manifest_path)
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["run_type"] == "INTRADAY_EVENT"
    assert payload["eligible_for_prediction"] is False
    assert payload["candidates"][0]["ticker"] == "ROIV"
    assert manifest["candidate_count"] == 1


def test_event_target_date_mismatch_is_rejected(tmp_path):
    session_path = tmp_path / "session.json"
    session_path.write_text(json.dumps(_session()), encoding="utf-8")
    premarket_root = tmp_path / "events"
    intraday_root = tmp_path / "intraday"
    _write_event(premarket_root, "ABC", "2026-08-31T11:30:00Z", target_date="2026-08-30")
    wrong_dir = premarket_root / "2026-08-31"
    wrong_dir.mkdir(parents=True, exist_ok=True)
    source = premarket_root / "2026-08-30" / "ABC-E1.json"
    (wrong_dir / "ABC-E1.json").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    with pytest.raises(ValueError, match="target date mismatch"):
        build_snapshot(
            session_path,
            premarket_root,
            intraday_root,
            tmp_path / "effective.json",
            tmp_path / "manifest.json",
        )
