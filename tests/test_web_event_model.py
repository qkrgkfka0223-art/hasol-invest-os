from __future__ import annotations

import pytest

from hasol_detector.web_event_model import SCHEMA_VERSION, normalize_payload


def _event(**overrides):
    row = {
        "ticker": "abc",
        "event_type": "CONTRACT",
        "event_published_at_utc": "2026-08-24T12:00:00Z",
        "official_source_url": "https://investor.example.com/release/1",
        "official_verified": True,
        "headline": "Award announced",
        "axis": "DEMAND",
    }
    row.update(overrides)
    return row


def test_dedupes_events_but_preserves_multi_event_ticker():
    e1 = _event(event_id="E1")
    e2 = _event(event_id="E2", event_type="GUIDANCE", headline="Guidance raised", official_source_url="https://investor.example.com/release/2")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "run_type": "PREMARKET",
        "eligible_for_prediction": True,
        "cutoff_et": "2026-08-24T09:25:00-04:00",
        "candidates": [e1, dict(e1), e2],
    }
    out = normalize_payload(payload)
    assert out["event_count_raw"] == 3
    assert out["event_count_deduped"] == 2
    assert out["candidate_count"] == 1
    assert out["candidates"][0]["event_count"] == 2
    assert "CONTRACT" in out["candidates"][0]["event_types"]
    assert "GUIDANCE" in out["candidates"][0]["event_types"]


def test_rejects_future_leakage():
    payload = {
        "schema_version": SCHEMA_VERSION,
        "run_type": "E2E_SIM",
        "eligible_for_prediction": True,
        "cutoff_et": "2026-08-24T09:25:00-04:00",
        "candidates": [_event(event_published_at_utc="2026-08-24T14:00:00Z")],
    }
    with pytest.raises(ValueError, match="future leakage"):
        normalize_payload(payload)


def test_production_requires_verified_primary_source():
    payload = {
        "schema_version": SCHEMA_VERSION,
        "run_type": "PREMARKET",
        "eligible_for_prediction": True,
        "cutoff_et": "2026-08-24T09:25:00-04:00",
        "candidates": [_event(official_verified=False)],
    }
    with pytest.raises(ValueError, match="verified"):
        normalize_payload(payload)
