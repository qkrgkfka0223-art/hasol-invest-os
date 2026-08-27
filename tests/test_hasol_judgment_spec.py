from __future__ import annotations

import copy
import pytest

from hasol_judgment.spec import fusion_score, rank_judgments, validate_judgment


def _record(ticker="AAA"):
    return {
        "ticker": ticker,
        "why_now": "new verified event before cutoff",
        "future_capital_flow": "contract converts into incremental demand",
        "next_buyer": "event-driven and growth funds",
        "market_missed": "revenue contribution is not fully reflected",
        "reflection_level": "PARTIAL",
        "price_acceptance": "ACCEPTED",
        "countercase": "event may be immaterial",
        "invalidation": "price loses event-day support",
        "chase_risk": "MEDIUM",
        "event_conviction_score": 80,
        "future_capital_flow_score": 85,
        "next_buyer_score": 75,
        "market_mispricing_score": 70,
        "price_acceptance_score": 78,
        "quant_score": 72,
        "source_quality_score": 95,
        "countercase_risk_score": 35,
        "chase_risk_score": 40,
    }


def test_fusion_score_is_deterministic():
    r = _record()
    assert fusion_score(r) == fusion_score(r)
    assert 0 <= fusion_score(r) <= 100


def test_missing_required_field_fails():
    r = _record()
    r["future_capital_flow"] = ""
    with pytest.raises(ValueError, match="future_capital_flow"):
        validate_judgment(r)


def test_rank_is_stable_under_input_reordering_and_assigns_top5():
    rows = []
    for i, ticker in enumerate(["EEE", "DDD", "CCC", "BBB", "AAA", "FFF"]):
        r = _record(ticker)
        r["future_capital_flow_score"] += i
        rows.append(r)
    a = rank_judgments(copy.deepcopy(rows))
    b = rank_judgments(list(reversed(copy.deepcopy(rows))))
    assert [r["ticker"] for r in a] == [r["ticker"] for r in b]
    assert [r["top5_rank"] for r in a[:5]] == [1, 2, 3, 4, 5]
    assert a[5]["top5_rank"] is None


def test_duplicate_ticker_fails():
    with pytest.raises(ValueError, match="duplicate"):
        rank_judgments([_record("AAA"), _record("AAA")])
