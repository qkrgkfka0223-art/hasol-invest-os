from __future__ import annotations

import pytest

from hasol_detector.web_event_model import SCHEMA_VERSION, normalize_payload


def _event(**overrides):
    row = {
        "ticker": "abc",
        "event_type": "CONTRACT",
        "event_published_at_utc": "2026-08-24T12:00:00Z",
        "official_source_url": "https://investor.example.com/release/1?utm_source=x",
        "official_verified": True,
        "headline": "Award announced",
        "axis": "DEMAND",
    }
    row.update(overrides)
    return row


def _payload(run_type="PREMARKET", eligible=True, candidates=None, cutoff="2026-08-24T09:25:00-04:00"):
    return {
        "schema_version": SCHEMA_VERSION,
        "run_type": run_type,
        "eligible_for_prediction": eligible,
        "prediction_date_et": "2026-08-24",
        "cutoff_et": cutoff,
        "candidates": candidates if candidates is not None else [_event()],
    }


def test_dedupes_headline_url_variants_but_preserves_multi_event_ticker():
    e1 = _event(event_id="E1")
    duplicate = _event(event_id="E1B", headline="Different syndicated headline", official_source_url="https://investor.example.com/release/1")
    e2 = _event(event_id="E2", event_type="GUIDANCE", headline="Guidance raised", official_source_url="https://investor.example.com/release/2")
    out = normalize_payload(_payload(candidates=[e1, duplicate, e2]))
    assert out["event_count_raw"] == 3
    assert out["event_count_deduped"] == 2
    assert out["candidate_count"] == 1
    assert out["candidates"][0]["event_count"] == 2
    assert out["candidates"][0]["official_source_url"] == "https://investor.example.com/release/2"


def test_rejects_future_leakage():
    with pytest.raises(ValueError, match="future leakage"):
        normalize_payload(_payload(run_type="E2E_SIM", candidates=[_event(event_published_at_utc="2026-08-24T14:00:00Z")]))


def test_production_requires_verified_primary_source():
    with pytest.raises(ValueError, match="verified"):
        normalize_payload(_payload(candidates=[_event(official_verified=False)]))


def test_prediction_cutoff_must_be_exactly_0925_et():
    with pytest.raises(ValueError, match="exactly"):
        normalize_payload(_payload(cutoff="2026-08-24T09:24:00-04:00"))


def test_intraday_event_can_never_modify_prediction():
    with pytest.raises(ValueError, match="must never"):
        normalize_payload(_payload(run_type="INTRADAY_EVENT", eligible=True))


def test_intraday_event_observation_is_allowed_when_not_prediction_eligible():
    out = normalize_payload(_payload(run_type="INTRADAY_EVENT", eligible=False, cutoff=None))
    assert out["run_type"] == "INTRADAY_EVENT"
    assert out["eligible_for_prediction"] is False
