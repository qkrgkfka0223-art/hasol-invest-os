from __future__ import annotations

import copy

import pytest

from scripts.validate_preopen_checkpoint import validate_checkpoint


def _checkpoint():
    return {
        "schema": "HASOL-PREOPEN-CHECKPOINT-v1",
        "checkpoint_id": "PREOPEN-20260901-012710Z-" + "a" * 16,
        "prediction_date_et": "2026-09-01",
        "captured_at_utc": "2026-09-01T01:27:10Z",
        "next_regular_open_et": "2026-09-01T09:30:00-04:00",
        "information_barrier": "ALPACA_REGULAR_OPEN",
        "source_commit": "b" * 40,
        "session_sha256": "c" * 64,
        "session_as_of_utc": "2026-09-01T01:20:00Z",
        "ledger_snapshot_input_sha256": "d" * 64,
        "ledger_manifest_sha256": "e" * 64,
        "ledger_manifest_file_sha256": "f" * 64,
        "effective_input_file_sha256": "1" * 64,
        "run_manifest_file_sha256": "2" * 64,
        "state_asof_file_sha256": "3" * 64,
        "live_quant_run_id": 123,
        "artifact_id": 456,
        "artifact_digest": "sha256:" + "4" * 64,
        "state_asof_valid": True,
        "source_coverage": {
            "SEC_EDGAR": "ATTEMPTED",
            "ISSUER_IR": "ATTEMPTED",
            "GLOBENEWSWIRE": "ATTEMPTED",
            "PRNEWSWIRE": "ATTEMPTED",
            "BUSINESS_WIRE": "ATTEMPTED",
            "ACCESS_NEWSWIRE": "ATTEMPTED",
            "FDA_REGULATORY": "ATTEMPTED",
            "EARNINGS_GUIDANCE_DIRECT": "ATTEMPTED",
        },
        "source_coverage_basis": "all required families checked during this pre-open state",
        "security_type_exclusions": [],
        "security_type_status": "PASS",
        "market_feed_status": "DEGRADED_IEX_DELAYED_SIP_REVALIDATED",
        "market_feed_validation": "5/5 IEX and delayed SIP",
        "candidate_count": 8,
        "eligible_count": 6,
        "ranked_count": 5,
        "market_data_coverage_pct": 100.0,
        "freeze_ready": True,
        "breadth_warning": True,
        "top20": ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"],
        "top5": [
            {"rank": 1, "ticker": "AAA", "quant_score": 90.0, "event_id": "E1"},
            {"rank": 2, "ticker": "BBB", "quant_score": 80.0, "event_id": "E2"},
            {"rank": 3, "ticker": "CCC", "quant_score": 70.0, "event_id": "E3"},
            {"rank": 4, "ticker": "DDD", "quant_score": 60.0, "event_id": "E4"},
            {"rank": 5, "ticker": "EEE", "quant_score": 50.0, "event_id": "E5"},
        ],
        "hasol_judgment": {"status": "VALID_PREOPEN_CHECKPOINT", "reason": "all gates passed"},
    }


def test_valid_checkpoint_passes():
    result = validate_checkpoint(_checkpoint())
    assert result["valid"] is True
    assert result["top5"] == ["AAA", "BBB", "CCC", "DDD", "EEE"]


def test_checkpoint_at_or_after_open_is_rejected():
    raw = _checkpoint()
    raw["captured_at_utc"] = "2026-09-01T13:30:00Z"
    with pytest.raises(ValueError, match="strictly before regular open"):
        validate_checkpoint(raw)


def test_future_session_asof_is_rejected():
    raw = _checkpoint()
    raw["session_as_of_utc"] = "2026-09-01T01:28:00Z"
    with pytest.raises(ValueError, match="after checkpoint capture"):
        validate_checkpoint(raw)


def test_missing_source_family_is_rejected():
    raw = _checkpoint()
    del raw["source_coverage"]["SEC_EDGAR"]
    with pytest.raises(ValueError, match="SEC_EDGAR"):
        validate_checkpoint(raw)


def test_unavailable_required_source_is_rejected():
    raw = _checkpoint()
    raw["source_coverage"]["PRNEWSWIRE"] = "UNAVAILABLE"
    with pytest.raises(ValueError, match="PRNEWSWIRE"):
        validate_checkpoint(raw)


def test_duplicate_top5_is_rejected():
    raw = _checkpoint()
    raw["top5"][4]["ticker"] = "AAA"
    with pytest.raises(ValueError, match="unique"):
        validate_checkpoint(raw)


def test_top20_top5_order_mismatch_is_rejected():
    raw = _checkpoint()
    raw["top20"][0], raw["top20"][1] = raw["top20"][1], raw["top20"][0]
    with pytest.raises(ValueError, match="match top5 rank order"):
        validate_checkpoint(raw)


def test_thin_but_valid_five_name_checkpoint_passes():
    raw = copy.deepcopy(_checkpoint())
    raw["candidate_count"] = 5
    raw["eligible_count"] = 5
    raw["ranked_count"] = 5
    raw["top20"] = raw["top20"][:5]
    assert validate_checkpoint(raw)["valid"] is True
