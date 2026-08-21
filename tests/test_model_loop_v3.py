from __future__ import annotations

import copy

from hasol_runtime import HasolRuntime


def make_payload(n: int = 25):
    rows = []
    for i in range(n):
        ticker = f"T{i:02d}"
        rows.append({
            "ticker": ticker,
            "exchange": "NASDAQ",
            "security_type": "COMMON_STOCK",
            "excluded_security_flag": False,
            "close": 10.0 + i,
            "adv20_usd": 20_000_000.0 + i * 1_000_000,
            "completed_sessions": 100,
            "price_source": "alpaca:test",
            "engine_raw": {
                "earnings_expectations": float(i),
                "future_flow_event": float(i * 2),
                "price_rs": float(i * 3),
                "supply_demand": float(i * 4),
                "quality": float(i * 5),
                "market_regime": float(i * 6),
            },
            "risk_penalty": float(i % 5),
            "compression": {
                "flow_clarity": 75,
                "evidence_freshness": 100,
                "price_acceptance": 75,
                "next_buyer_clarity": 75,
                "priced_in_asymmetry": 50,
                "risk_resilience": 75,
            },
            "evidence": [{
                "type": "SEC",
                "published_at_utc": "2026-08-19T18:00:00+00:00",
                "ref": f"sec:test:{ticker}",
                "claim": "test primary evidence",
                "freshness": "FRESH",
            }],
            "thesis": "future capital flow test thesis",
            "counter_thesis": "strongest opposing hypothesis",
            "invalidation": "invalidate if primary thesis evidence reverses",
        })
    return {
        "run": {
            "run_id": "RUN-20260819-CLOSE-P11-R10",
            "cutoff_et": "2026-08-19T16:00:00-04:00",
            "strategy_version": "HASOL-PREDICTOR-v1.1-CANDIDATE",
            "ruleset_version": "HASOL-RULESET-v1.0",
            "snapshot_ref": "artifact://test/20260819",
        },
        "coverage": {
            "eligible_expected": n,
            "market_data_observed": n,
        },
        "market_regime": "NEUTRAL",
        "market_regime_engine_version": "REGIME-TEST-v1",
        "universe": rows,
    }


def test_identical_input_produces_identical_hash_and_ranks():
    first = HasolRuntime(make_payload()).run()
    second = HasolRuntime(make_payload()).run()
    assert first["state"] == "WRITE_READY"
    assert first["official_prediction"] is False
    assert first["prediction_hash"] == second["prediction_hash"]
    assert [r["ticker"] for r in first["prediction"]["top20"]] == [r["ticker"] for r in second["prediction"]["top20"]]
    assert len(first["prediction"]["top20"]) == 20
    assert len(first["prediction"]["top5_tickers"]) == 5


def test_broken_coverage_never_becomes_no_candidate():
    payload = make_payload()
    payload["coverage"]["market_data_observed"] = 20
    result = HasolRuntime(payload).run()
    assert result["outcome"] == "INVALID_DATA"
    assert result["official_prediction"] is False
    assert "coverage" in result["errors"][0]


def test_future_evidence_fails_closed():
    payload = make_payload()
    payload["universe"][0]["evidence"][0]["published_at_utc"] = "2026-08-20T01:00:00+00:00"
    result = HasolRuntime(payload).run()
    assert result["outcome"] == "INVALID_EVIDENCE"
    assert result["official_prediction"] is False


def test_readback_hash_is_required_for_official_close():
    result = HasolRuntime(make_payload()).run()
    bad = HasolRuntime.close_after_readback(result, "wrong")
    assert bad["outcome"] == "INVALID_PERSISTENCE"
    assert bad["official_prediction"] is False

    good = HasolRuntime.close_after_readback(result, result["prediction_hash"])
    assert good["state"] == "CLOSED"
    assert good["official_prediction"] is True


def test_missing_thesis_fails_closed():
    payload = make_payload()
    del payload["universe"][3]["thesis"]
    result = HasolRuntime(payload).run()
    assert result["official_prediction"] is False
    assert result["outcome"] == "INVALID_DATA"
