from __future__ import annotations

import copy

import pytest

from scripts.validate_preopen_checkpoint import validate_checkpoint


def _checkpoint():
    capture = "2026-09-01T01:27:10Z"
    families = (
        "SEC_EDGAR", "ISSUER_IR", "GLOBENEWSWIRE", "PRNEWSWIRE",
        "BUSINESS_WIRE", "ACCESS_NEWSWIRE", "FDA_REGULATORY", "EARNINGS_GUIDANCE_DIRECT",
    )
    details = {
        family: {
            "status": "ATTEMPTED",
            "scanned_at_utc": "2026-09-01T01:10:00Z",
            "window_end_utc": "2026-09-01T01:10:00Z",
        }
        for family in families
    }
    top20 = [f"A{i:02d}" for i in range(1, 21)]
    provenance = {
        ticker: {
            "source": "EVENT" if i <= 10 else "FULL_MARKET_QUANT_BACKSTOP",
            "score": 100.0 - i,
            "evidence_ref": f"E{i}" if i <= 10 else f"FULLRANK:{i}",
        }
        for i, ticker in enumerate(top20, start=1)
    }
    return {
        "schema": "HASOL-PREOPEN-CHECKPOINT-v1",
        "validation_contract": "HASOL-PREOPEN-STRICT-v1",
        "top20_contract": "HASOL-TOP20-EXACT-v1",
        "top20_count": 20,
        "top20_provenance": provenance,
        "backstop_count": 10,
        "backstop_asof_utc": "2026-09-01T01:20:00Z",
        "checkpoint_id": "PREOPEN-20260901-012710Z-" + "a" * 16,
        "prediction_date_et": "2026-09-01",
        "captured_at_utc": capture,
        "next_regular_open_et": "2026-09-01T09:30:00-04:00",
        "information_barrier": "ALPACA_REGULAR_OPEN",
        "source_commit": "b" * 40,
        "artifact_source_commit": "b" * 40,
        "session_sha256": "c" * 64,
        "session_as_of_utc": "2026-09-01T01:20:00Z",
        "ledger_snapshot_input_sha256": "d" * 64,
        "run_input_sha256": "d" * 64,
        "ledger_manifest_sha256": "e" * 64,
        "ledger_manifest_file_sha256": "f" * 64,
        "effective_input_file_sha256": "1" * 64,
        "run_manifest_file_sha256": "2" * 64,
        "state_asof_file_sha256": "3" * 64,
        "live_quant_run_id": 123,
        "artifact_id": 456,
        "artifact_digest": "sha256:" + "4" * 64,
        "state_asof_valid": True,
        "source_coverage": {family: detail["status"] for family, detail in details.items()},
        "source_coverage_detail": details,
        "source_coverage_basis": "all required families checked during this pre-open state",
        "security_type_exclusions": [],
        "security_type_status": "PASS",
        "security_type_validated_at_utc": "2026-09-01T01:15:00Z",
        "market_feed_status": "DEGRADED_IEX_DELAYED_SIP_REVALIDATED",
        "market_feed_validation": "20/20 common-stock universe and Top5 feed revalidated",
        "market_feed_validated_at_utc": "2026-09-01T01:20:00Z",
        "candidate_count": 24,
        "eligible_count": 22,
        "ranked_count": 20,
        "market_data_coverage_pct": 100.0,
        "freeze_ready": True,
        "breadth_warning": False,
        "top20": top20,
        "top5": [
            {"rank": i, "ticker": f"A{i:02d}", "quant_score": 100.0 - i, "event_id": f"E{i}", "provenance": "EVENT"}
            for i in range(1, 6)
        ],
        "hasol_judgment": {"status": "VALID_PREOPEN_CHECKPOINT", "reason": "all exact Top20 gates passed"},
    }


def _legacy():
    raw = copy.deepcopy(_checkpoint())
    for key in ("top20_contract", "top20_count", "top20_provenance", "backstop_count", "backstop_asof_utc"):
        raw.pop(key, None)
    raw["candidate_count"] = 8
    raw["eligible_count"] = 6
    raw["ranked_count"] = 6
    raw["top20"] = raw["top20"][:6]
    for row in raw["top5"]:
        row.pop("provenance", None)
    return raw


def test_valid_checkpoint_is_exact_top20_promotion_eligible():
    result = validate_checkpoint(_checkpoint())
    assert result["valid"] is True
    assert result["strict_valid"] is True
    assert result["promotion_eligible"] is True
    assert result["top20_count"] == 20
    assert result["top5"] == ["A01", "A02", "A03", "A04", "A05"]


def test_old_strict_checkpoint_remains_archive_but_not_promotion_eligible():
    result = validate_checkpoint(_legacy())
    assert result["valid"] is True
    assert result["strict_valid"] is False
    assert result["promotion_eligible"] is False
    assert result["archive_class"] == "LEGACY_IMMUTABLE_ARCHIVE"


def test_checkpoint_at_or_after_open_is_rejected():
    raw = _checkpoint(); raw["captured_at_utc"] = "2026-09-01T13:30:00Z"
    with pytest.raises(ValueError, match="strictly before regular open"): validate_checkpoint(raw)


def test_future_session_asof_is_rejected():
    raw = _checkpoint(); raw["session_as_of_utc"] = "2026-09-01T01:28:00Z"
    with pytest.raises(ValueError, match="after checkpoint capture"): validate_checkpoint(raw)


def test_missing_source_family_is_rejected():
    raw = _checkpoint(); del raw["source_coverage"]["SEC_EDGAR"]
    with pytest.raises(ValueError, match="SEC_EDGAR"): validate_checkpoint(raw)


def test_unavailable_required_source_is_rejected():
    raw = _checkpoint(); raw["source_coverage"]["PRNEWSWIRE"] = "UNAVAILABLE"
    with pytest.raises(ValueError, match="PRNEWSWIRE"): validate_checkpoint(raw)


def test_recovered_attempt_status_is_accepted():
    raw = _checkpoint()
    raw["source_coverage"]["SEC_EDGAR"] = "ATTEMPTED_AND_RECOVERED"
    raw["source_coverage_detail"]["SEC_EDGAR"]["status"] = "ATTEMPTED_AND_RECOVERED"
    assert validate_checkpoint(raw)["promotion_eligible"] is True


def test_strict_contract_requires_information_barrier():
    raw = _checkpoint(); raw.pop("information_barrier")
    with pytest.raises(ValueError, match="information_barrier"): validate_checkpoint(raw)


def test_strict_contract_requires_state_asof_proof():
    raw = _checkpoint(); raw.pop("state_asof_valid")
    with pytest.raises(ValueError, match="state_asof_valid"): validate_checkpoint(raw)


def test_strict_contract_rejects_mismatched_run_input():
    raw = _checkpoint(); raw["run_input_sha256"] = "9" * 64
    with pytest.raises(ValueError, match="run_input_sha256 must equal"): validate_checkpoint(raw)


def test_strict_contract_rejects_mismatched_artifact_commit():
    raw = _checkpoint(); raw["artifact_source_commit"] = "a" * 40
    with pytest.raises(ValueError, match="artifact_source_commit"): validate_checkpoint(raw)


def test_stale_source_scan_is_rejected():
    raw = _checkpoint(); raw["source_coverage_detail"]["SEC_EDGAR"]["scanned_at_utc"] = "2026-08-31T23:00:00Z"
    with pytest.raises(ValueError, match="stale"): validate_checkpoint(raw)


def test_stale_market_feed_validation_is_rejected():
    raw = _checkpoint(); raw["market_feed_validated_at_utc"] = "2026-09-01T00:30:00Z"
    with pytest.raises(ValueError, match="stale"): validate_checkpoint(raw)


def test_duplicate_top5_is_rejected():
    raw = _checkpoint(); raw["top5"][4]["ticker"] = "A01"
    with pytest.raises(ValueError, match="unique"): validate_checkpoint(raw)


def test_top20_top5_order_mismatch_is_rejected():
    raw = _checkpoint(); raw["top20"][0], raw["top20"][1] = raw["top20"][1], raw["top20"][0]
    with pytest.raises(ValueError, match="match top5 rank order"): validate_checkpoint(raw)


def test_exact_contract_rejects_19_names():
    raw = _checkpoint()
    removed = raw["top20"].pop()
    raw["top20_provenance"].pop(removed)
    raw["top20_count"] = 19
    raw["backstop_count"] = 9
    with pytest.raises(ValueError, match="exactly 20"): validate_checkpoint(raw)


def test_exact_contract_rejects_missing_provenance():
    raw = _checkpoint(); raw["top20_provenance"].pop("A20")
    with pytest.raises(ValueError, match="keys must match"): validate_checkpoint(raw)


def test_exact_contract_rejects_bad_provenance_source():
    raw = _checkpoint(); raw["top20_provenance"]["A20"]["source"] = "PAD"
    with pytest.raises(ValueError, match="invalid top20 provenance source"): validate_checkpoint(raw)


def test_exact_contract_rejects_wrong_backstop_count():
    raw = _checkpoint(); raw["backstop_count"] = 9
    with pytest.raises(ValueError, match="backstop_count"): validate_checkpoint(raw)


def test_legacy_six_name_checkpoint_cannot_promote():
    result = validate_checkpoint(_legacy())
    assert result["promotion_eligible"] is False
    assert result["top20_count"] == 6
