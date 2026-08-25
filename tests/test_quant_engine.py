from __future__ import annotations

import numpy as np
import pandas as pd

from hasol_quant.features import build_features
from hasol_quant.ranker import rank_universe, top_n
from hasol_quant.universe import apply_market_liquidity_gate


def make_bars(ticker: str, start: float, daily_drift: float, volume: float, n: int = 75) -> pd.DataFrame:
    rows = []
    price = start
    for i in range(n):
        prev = price
        price = prev * (1 + daily_drift)
        o = prev * 1.001
        h = max(o, price) * 1.01
        l = min(o, price) * 0.99
        rows.append({
            "ticker": ticker,
            "timestamp": pd.Timestamp("2026-04-01", tz="UTC") + pd.Timedelta(days=i),
            "open": o, "high": h, "low": l, "close": price,
            "volume": volume * (1 + (i % 5) * 0.03), "trade_count": 1000 + i, "vwap": (o + price) / 2,
        })
    return pd.DataFrame(rows)


def test_features_and_rank_are_deterministic():
    bars = pd.concat([
        make_bars("SPY", 700, 0.0010, 40_000_000),
        make_bars("AAA", 20, 0.0040, 2_000_000),
        make_bars("BBB", 30, 0.0015, 2_000_000),
        make_bars("CCC", 10, -0.0010, 3_000_000),
    ], ignore_index=True)
    f1, f2 = build_features(bars), build_features(bars)
    pd.testing.assert_frame_equal(f1.sort_values("ticker").reset_index(drop=True), f2.sort_values("ticker").reset_index(drop=True), check_dtype=False)
    r1, r2 = rank_universe(f1, {"AAA", "BBB", "CCC"}), rank_universe(f2, {"AAA", "BBB", "CCC"})
    pd.testing.assert_series_equal(r1["ticker"], r2["ticker"])
    np.testing.assert_allclose(r1["quant_score"], r2["quant_score"], equal_nan=True)
    assert r1.iloc[0]["ticker"] == "AAA"


def test_liquidity_gate():
    universe = pd.DataFrame({"ticker": ["AAA", "BBB", "CCC"]})
    features = pd.DataFrame({
        "ticker": ["AAA", "BBB", "CCC"], "close": [10.0, 2.5, 20.0],
        "adv20_usd": [15_000_000, 20_000_000, 5_000_000], "history_bars": [30, 30, 30],
    })
    out = apply_market_liquidity_gate(universe, features)
    assert out["ticker"].tolist() == ["AAA"]


def test_top_n_excludes_null_scores():
    df = pd.DataFrame({"ticker": ["A", "B", "C"], "quant_score": [90.0, np.nan, 80.0]})
    assert top_n(df, 2)["ticker"].tolist() == ["A", "C"]
