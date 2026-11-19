"""Synthetic failure reproductions; never connect to trading or Sheets."""
import copy
import json
import subprocess
import sys

from scripts.audit_discovery_freshness import audit


def sample():
    return {
        "schema": "HASOL-PREFREEZE-v1",
        "run_id": "RUN-TEST-HASOL-001",
        "run_market_date": "2026-11-17",
        "last_completed_regular_session": "2026-11-16",
        "blind_locked_at_utc": "2026-11-17T12:50:00Z",
        "first_price_exposure_at_utc": "2026-11-17T12:51:00Z",
        "cutoff_utc": "2026-11-17T13:02:10Z",
        "candidate_packets": [{
            "ticker": "SLS", "discovered_at_utc": "2026-11-17T12:10:00Z",
            "last_issuer_review_at_utc": "2026-11-17T12:30:00Z",
            "handled_release_ids": ["SLS-20261117-PH3"],
        }],
        "issuer_releases": [{
            "release_id": "SLS-20261117-PH3", "ticker": "SLS",
            "published_at_utc": "2026-11-17T12:00:00Z",
            "collected_at_utc": "2026-11-17T12:06:00Z",
            "primary_url": "https://issuer.example.test/sls/phase3",
            "source_verified": True, "full_original_checked": True,
            "material": True,
        }],
        "issuer_sweeps": [
            {"completed_at_utc": "2026-11-17T12:48:00Z", "primary_issuer_only": True,
             "price_reaction_preview": False, "feed_coverage_verified": True},
            {"completed_at_utc": "2026-11-17T12:59:00Z", "primary_issuer_only": True,
             "price_reaction_preview": False, "feed_coverage_verified": True},
        ],
        "lagged_leader_batches": [{
            "session_date": "2026-11-16", "available_at_utc": "2026-11-17T10:00:00Z",
            "tickers": ["SLS", "CLRO"] + [f"T{i:03d}" for i in range(98)],
            "publisher_data_verified": True,
        }],
        "shadow_discovery_tickers": ["SLS", "CLRO"] + [f"T{i:03d}" for i in range(98)],
        "live_mover_snapshots": [{
            "asof_utc": "2026-11-17T12:56:00Z",
            "discovery_class": "AFTER_PRICE_DISCOVERY",
        }],
        "full_pit_eligible_roster_verified": True,
        "release_feed_completeness_independently_confirmed": True,
    }


def test_complete_synthetic_evidence_only_candidate_for_external_verification():
    x = audit(sample())
    assert x["decision"] == "EVIDENCE_READY_REQUIRES_INDEPENDENT_VERIFY"
    assert x["metrics"]["material_releases_handled"] == 1
    assert x["metrics"]["external_market_or_issuer_data_authenticated_by_this_script"] is False


def test_sls_original_failure_is_blocked_before_freeze():
    x = sample()
    x["candidate_packets"][0]["handled_release_ids"] = []
    result = audit(x)
    assert result["decision"] == "BLOCK"
    assert any("MATERIAL_ISSUER_RELEASE_NOT_HANDLED" in e for e in result["errors"])


def test_sls_missing_candidate_but_release_found_is_blocked():
    x = sample()
    x["candidate_packets"] = []
    result = audit(x)
    assert result["decision"] == "BLOCK"
    assert any("SLS" in e for e in result["errors"])


def test_after_blind_new_release_cannot_be_called_clean():
    x = sample()
    x["issuer_releases"][0]["published_at_utc"] = "2026-11-17T12:55:00Z"
    x["issuer_releases"][0]["collected_at_utc"] = "2026-11-17T12:56:00Z"
    x["candidate_packets"][0]["last_issuer_review_at_utc"] = "2026-11-17T12:57:00Z"
    result = audit(x)
    assert result["decision"] == "OFFICIAL_PARTIAL_NOT_CLEAN"
    assert any("after Price-Blind lock" in e for e in result["degraded"])


def test_market_reaction_before_blind_degrades():
    x = sample()
    x["first_price_exposure_at_utc"] = "2026-11-17T12:45:00Z"
    result = audit(x)
    assert result["decision"] == "OFFICIAL_PARTIAL_NOT_CLEAN"
    assert any("chronology" in e for e in result["degraded"])


def test_missing_recent_issuer_refresh_degrades():
    x = sample()
    x["issuer_sweeps"] = x["issuer_sweeps"][:1]
    result = audit(x)
    assert result["decision"] == "OFFICIAL_PARTIAL_NOT_CLEAN"
    assert any("15 minutes" in e for e in result["degraded"])


def test_unverified_original_source_degrades():
    x = sample()
    x["issuer_releases"][0]["full_original_checked"] = False
    assert audit(x)["decision"] == "OFFICIAL_PARTIAL_NOT_CLEAN"


def test_same_day_close_as_lagged_is_lookahead_and_blocks():
    x = sample()
    x["lagged_leader_batches"][0]["session_date"] = "2026-11-17"
    result = audit(x)
    assert result["decision"] == "BLOCK"
    assert any("future data" in e for e in result["errors"])


def test_future_mover_snapshot_is_lookahead():
    x = sample()
    x["live_mover_snapshots"][0]["asof_utc"] = "2026-11-17T14:00:00Z"
    assert audit(x)["decision"] == "BLOCK"


def test_missing_lagged_shadow_candidate_does_not_silently_pass():
    x = sample()
    x["shadow_discovery_tickers"] = ["SLS"]
    result = audit(x)
    assert result["decision"] == "OFFICIAL_PARTIAL_NOT_CLEAN"
    assert any("not fully carried" in e for e in result["degraded"])


def test_unknown_pit_universe_or_unverified_feed_never_clean():
    x = sample()
    x["full_pit_eligible_roster_verified"] = False
    x["release_feed_completeness_independently_confirmed"] = False
    result = audit(x)
    assert result["decision"] == "OFFICIAL_PARTIAL_NOT_CLEAN"
    assert any("PIT" in e for e in result["degraded"])


def test_missing_required_provenance_blocks():
    x = sample()
    x.pop("issuer_sweeps")
    assert audit(x)["decision"] == "BLOCK"


def test_blank_or_future_collection_blocks():
    x = sample()
    x["issuer_releases"][0]["collected_at_utc"] = "2026-11-17T14:01:00Z"
    assert audit(x)["decision"] == "BLOCK"


def test_rechecks_no_loss_of_history():
    x = sample()
    before = copy.deepcopy(x)
    assert audit(x)["decision"] == audit(x)["decision"]
    assert x == before


def test_cli_decision_codes(tmp_path):
    fn = tmp_path / "sample.json"
    cmd = [sys.executable, "-m", "scripts.audit_discovery_freshness", "--input", str(fn)]
    fn.write_text(json.dumps(sample()), encoding="utf-8")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert result.returncode == 0
    x = sample()
    x["candidate_packets"][0]["handled_release_ids"] = []
    fn.write_text(json.dumps(x), encoding="utf-8")
    assert subprocess.run(cmd, capture_output=True, text=True, check=False).returncode == 2
    x = sample()
    x["full_pit_eligible_roster_verified"] = False
    fn.write_text(json.dumps(x), encoding="utf-8")
    assert subprocess.run(cmd + ["--require-evidence-ready"], capture_output=True, text=True, check=False).returncode == 3


def test_nullable_missing_provenance_does_not_crash_or_certify():
    x = sample()
    x["issuer_releases"][0]["primary_url"] = None
    x["shadow_discovery_tickers"] = None
    result = audit(x)
    assert result["decision"] == "OFFICIAL_PARTIAL_NOT_CLEAN"
    assert any("primary issuer URL" in e for e in result["degraded"])


def test_duplicate_lagged_symbols_is_blocked():
    x = sample()
    x["lagged_leader_batches"][0]["tickers"] = ["SLS", "SLS"]
    assert audit(x)["decision"] == "BLOCK"


def test_ambiguous_materiality_must_not_bypass_latest_release_check():
    x = sample()
    x["issuer_releases"][0]["material"] = "FALSE"
    assert audit(x)["decision"] == "BLOCK"


def test_unknown_price_preview_cannot_certify_price_blind():
    x = sample()
    x["issuer_sweeps"][0].pop("price_reaction_preview")
    assert audit(x)["decision"] == "OFFICIAL_PARTIAL_NOT_CLEAN"


def test_incomplete_lagged_top100_cannot_be_clean():
    x = sample()
    x["lagged_leader_batches"][0]["tickers"] = ["SLS", "CLRO"]
    x["shadow_discovery_tickers"] = ["SLS", "CLRO"]
    assert audit(x)["decision"] == "OFFICIAL_PARTIAL_NOT_CLEAN"


def test_non_list_handled_release_ids_does_not_crash():
    x = sample()
    x["candidate_packets"][0]["handled_release_ids"] = None
    assert audit(x)["decision"] == "BLOCK"
