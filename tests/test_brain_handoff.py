from __future__ import annotations

import copy
import json
import subprocess
import sys

from scripts.validate_brain_handoff import SCHEMA, validate


RUN_ID = "RUN-TEST-HASOL-001"


def fixture():
    """Synthetic ONLY. No actual prediction or market data."""
    predictions = []
    frozen = []
    outcomes = []
    for i in range(1, 41):
        ticker = f"T{i:03d}"
        row = {
            "RUN_ID": RUN_ID,
            "TICKER_SNAPSHOT": ticker,
            "OFFICIAL_MODEL_RANK": str(i),
            "MODEL_TOP20": "TRUE" if i <= 20 else "FALSE",
            "TOP5": "TRUE" if i <= 5 else "FALSE",
            "DISCOVERY_CLASS": "ISSUER_PRIMARY_RELEASE",
            "SOURCE_REF": f"https://issuer.example.com/{ticker}",
            "ISSUER_RELEASED_AT_UTC": "2026-11-17T12:00:00Z",
            "BLIND_PACKET_AT_UTC": "2026-11-17T12:30:00Z",
            "BLIND_FACTS_SUMMARY": f"{ticker} synthetic revenue +20%",
            "BLIND_JUDGMENT": "Scenario not yet reflected in price",
            "source_independently_verified": True,
        }
        predictions.append(row)
        if i <= 20:
            frozen.append({
                "RUN_ID": RUN_ID,
                "TICKER_SNAPSHOT": ticker,
                "RANK": str(i),
                "TOP5": "TRUE" if i <= 5 else "FALSE",
                "BASELINE_PRICE": "10.00",
                "BASELINE_OBSERVED_AT_UTC": "2026-11-17T12:59:20Z",
                "FROZEN_AT_UTC": "2026-11-17T13:00:00Z",
                "LOCK": "LOCKED",
                "PRICE_SOURCE": "SYNTHETIC_ONLY",
                "eligibility": {
                    "exchange": "NASDAQ",
                    "security_type": "COMMON_STOCK",
                    "listed_sessions": 25,
                    "price": 10.0,
                    "adtv20_usd": 20_000_000,
                },
            })
            outcomes.append({
                "RUN_ID": RUN_ID,
                "TICKER_SNAPSHOT": ticker,
                "RANK": str(i),
                "BASELINE_PRICE": "10.00",
            })
    return {
        "schema": SCHEMA,
        "run_id": RUN_ID,
        "blind_locked_at_utc": "2026-11-17T12:30:30Z",
        "first_market_data_access_at_utc": "2026-11-17T12:31:00Z",
        "predictions": predictions,
        "frozen": frozen,
        "outcomes": outcomes,
        "universe": {
            "complete": True,
            "snapshot_sha256": "a" * 64,
            "asof_utc": "2026-11-17T12:45:00Z",
            "independently_verified": True,
        },
        "shadow": {"method": "SIMPLE_ATR20_V1", "status": "UNSCORABLE"},
    }


def test_synthetic_complete_evidence_is_only_a_candidate_not_a_clean_certificate():
    out = validate(fixture())
    assert out["decision"] == "EVIDENCE_READY_REQUIRES_INDEPENDENT_VERIFY"
    assert out["errors"] == []
    assert out["degraded"] == []
    assert out["metrics"]["frozen"] == 20
    assert out["metrics"]["ranked"] == 40
    assert out["metrics"]["external_issuer_source_verified_by_this_script"] is False


def test_after_price_challenger_never_becomes_clean_from_structural_pass():
    data = fixture()
    data["predictions"][0]["DISCOVERY_CLASS"] = "AFTER_PRICE_PRIOR_RUN_CHALLENGER"
    out = validate(data)
    assert out["decision"] == "OFFICIAL_PARTIAL_NOT_CLEAN"
    assert any("issuer-first" in x for x in out["degraded"])


def test_market_data_before_blind_lock_downgrades():
    data = fixture()
    data["first_market_data_access_at_utc"] = "2026-11-17T12:00:00Z"
    out = validate(data)
    assert out["decision"] == "OFFICIAL_PARTIAL_NOT_CLEAN"
    assert any("preceded" in x for x in out["degraded"])


def test_stale_baseline_downgrades_with_exact_count():
    data = fixture()
    data["frozen"][0]["BASELINE_OBSERVED_AT_UTC"] = "2026-11-17T12:40:00Z"
    out = validate(data)
    assert out["decision"] == "OFFICIAL_PARTIAL_NOT_CLEAN"
    assert out["metrics"]["stale_baseline_count"] == 1


def test_unknown_universe_does_not_become_clean():
    data = fixture()
    data["universe"] = {"complete": False}
    out = validate(data)
    assert out["decision"] == "OFFICIAL_PARTIAL_NOT_CLEAN"
    assert any("UNKNOWN" in x for x in out["degraded"])


def test_missing_eligibility_blocks_freeze():
    data = fixture()
    data["frozen"][0].pop("eligibility")
    out = validate(data)
    assert out["decision"] == "BLOCK"
    assert any("eligibility missing" in x for x in out["errors"])


def test_failed_price_or_adv_blocks_freeze():
    data = fixture()
    data["frozen"][3]["eligibility"]["adtv20_usd"] = 9_000_000
    out = validate(data)
    assert out["decision"] == "BLOCK"
    assert any("fails eligibility" in x for x in out["errors"])


def test_rank_zero_top20_or_flag_mismatch_blocks_freeze():
    data = fixture()
    data["predictions"][0]["OFFICIAL_MODEL_RANK"] = "0"
    out = validate(data)
    assert out["decision"] == "BLOCK"
    assert any("rank" in x.lower() for x in out["errors"])


def test_duplicate_prediction_and_duplicate_rank_are_caught():
    data = fixture()
    data["predictions"].append(copy.deepcopy(data["predictions"][0]))
    data["predictions"][1]["OFFICIAL_MODEL_RANK"] = "1"
    out = validate(data)
    assert out["decision"] == "BLOCK"
    assert any("duplicate ticker" in x for x in out["errors"])
    assert any("contiguous" in x for x in out["errors"])


def test_outcome_baseline_or_top5_mismatch_blocks():
    data = fixture()
    data["outcomes"][0]["BASELINE_PRICE"] = "10.01"
    data["frozen"][1]["TOP5"] = "FALSE"
    out = validate(data)
    assert out["decision"] == "BLOCK"
    assert any("Outcome" in x for x in out["errors"])
    assert any("Top5" in x for x in out["errors"])


def test_scorable_shadow_requires_pre_frozen_deterministic_same_frontier():
    data = fixture()
    data["shadow"] = {
        "method": "SIMPLE_ATR20_V1",
        "status": "SCORABLE",
        "scored_at_utc": "2026-11-17T12:58:00Z",
        "scores": [{"ticker": f"T{i:03d}", "score": 100 - i, "rank": i} for i in range(1, 41)],
    }
    out = validate(data)
    assert out["decision"] == "EVIDENCE_READY_REQUIRES_INDEPENDENT_VERIFY"
    data["shadow"]["scores"][0]["rank"] = 40
    out = validate(data)
    assert out["decision"] == "OFFICIAL_PARTIAL_NOT_CLEAN"
    assert any("ranks" in x for x in out["degraded"])


def test_cli_exit_codes(tmp_path):
    raw = tmp_path / "snapshot.json"
    output = tmp_path / "qa.json"
    raw.write_text(json.dumps(fixture()), encoding="utf-8")
    cmd = [sys.executable, "-m", "scripts.validate_brain_handoff", "--input", str(raw), "--output", str(output)]
    good = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert good.returncode == 0
    assert json.loads(output.read_text())["decision"] == "EVIDENCE_READY_REQUIRES_INDEPENDENT_VERIFY"
    changed = fixture()
    changed["frozen"].pop()
    raw.write_text(json.dumps(changed), encoding="utf-8")
    bad = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert bad.returncode == 2
    partial = fixture()
    partial["universe"]["complete"] = False
    raw.write_text(json.dumps(partial), encoding="utf-8")
    strict = subprocess.run(cmd + ["--require-evidence-ready"], capture_output=True, text=True, check=False)
    assert strict.returncode == 3


def test_source_release_after_blind_packet_is_not_price_blind():
    data = fixture()
    data["predictions"][0]["ISSUER_RELEASED_AT_UTC"] = "2026-11-17T12:30:10Z"
    out = validate(data)
    assert out["decision"] == "OFFICIAL_PARTIAL_NOT_CLEAN"
    assert any("look-ahead" in x for x in out["degraded"])


def test_malformed_rank_cannot_crash_or_pass():
    data = fixture()
    data["predictions"][0]["OFFICIAL_MODEL_RANK"] = "UNKNOWN"
    out = validate(data)
    assert out["decision"] == "BLOCK"
    assert any("rank" in x for x in out["errors"])


def test_missing_baseline_timestamp_is_degraded_not_invented():
    data = fixture()
    data["frozen"][0].pop("BASELINE_OBSERVED_AT_UTC")
    out = validate(data)
    assert out["decision"] == "OFFICIAL_PARTIAL_NOT_CLEAN"
    assert any("timestamp missing" in x for x in out["degraded"])
