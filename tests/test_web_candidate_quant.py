from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import run_web_candidate_quant as mod


def _bars(tickers=None, low_liquidity=False) -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2026-04-01", periods=80, freq="B", tz="UTC")
    tickers = tickers or ["AAA", "BBB", "CCC", "DDD", "EEE"]
    for j, ticker in enumerate(tickers + ["SPY"]):
        base = 500.0 if ticker == "SPY" else 20.0 + j * 5
        vol = 50_000_000 if ticker == "SPY" else (10_000 if low_liquidity else 1_500_000 + j * 100_000)
        for i, ts in enumerate(dates):
            drift = 0.001 if ticker == "SPY" else 0.001 + j * 0.0003
            close = base * (1 + i * drift)
            rows.append({
                "ticker": ticker,
                "timestamp": ts,
                "open": close * 0.995,
                "high": close * 1.01,
                "low": close * 0.99,
                "close": close,
                "volume": float(vol * (1 + (i % 5) * 0.05)),
                "trade_count": np.nan,
                "vwap": np.nan,
            })
    return pd.DataFrame(rows)


def _event(ticker: str, event_id: str) -> dict:
    return {
        "ticker": ticker,
        "event_id": event_id,
        "event_type": "CONTRACT",
        "axis": "TEST",
        "event_published_at_utc": "2026-08-25T11:00:00Z",
        "official_source_url": f"https://investor.example.com/{event_id}",
        "official_verified": True,
        "headline": f"{event_id} headline",
    }


def _payload(tickers):
    return {
        "schema_version": "HASOL-WEB-CANDIDATES-v2",
        "run_type": "E2E_SIM",
        "eligible_for_prediction": True,
        "prediction_date_et": "2026-08-26",
        "cutoff_et": "2026-08-26T09:25:00-04:00",
        "candidates": [_event(t, f"E{i}") for i, t in enumerate(tickers, start=1)],
    }


def test_candidate_quant_is_deterministic_noncanonical_and_freeze_ready(tmp_path: Path, monkeypatch) -> None:
    tickers = ["AAA", "BBB", "CCC", "DDD", "EEE"]
    source = tmp_path / "input.json"
    source.write_text(json.dumps(_payload(tickers)), encoding="utf-8")
    monkeypatch.setattr(mod, "fetch_daily_bars", lambda *args, **kwargs: _bars(tickers))

    out1, out2 = tmp_path / "o1", tmp_path / "o2"
    m1 = mod.run(source, out1)
    m2 = mod.run(source, out2)

    assert m1["quant_market_source"] == "YAHOO_YFINANCE_DETECTION_ONLY"
    assert m1["final_market_validator"] == "ALPACA_CONNECTED_APP"
    assert m1["input_sha256"] == m2["input_sha256"]
    assert m1["quality"]["freeze_ready"] is True
    assert m1["quality"]["quality_status"] == "PASS"
    assert m1["quality"]["breadth_warning"] is True
    a = pd.read_csv(out1 / "web_candidate_quant.csv")
    b = pd.read_csv(out2 / "web_candidate_quant.csv")
    pd.testing.assert_frame_equal(a, b)
    assert set(a["ticker"]) == set(tickers)


def test_zero_eligible_candidates_cannot_freeze(tmp_path: Path, monkeypatch) -> None:
    tickers = ["AAA", "BBB", "CCC", "DDD", "EEE"]
    source = tmp_path / "input.json"
    source.write_text(json.dumps(_payload(tickers)), encoding="utf-8")
    monkeypatch.setattr(mod, "fetch_daily_bars", lambda *args, **kwargs: _bars(tickers, low_liquidity=True))
    manifest = mod.run(source, tmp_path / "out")
    assert manifest["quality"]["quant_eligible"] == 0
    assert manifest["quality"]["freeze_ready"] is False
    assert manifest["quality"]["quality_status"] == "NO_PREDICTION"
    assert "QUANT_ELIGIBLE_LT_5" in manifest["quality"]["quality_reasons"]


def test_invalid_schema_rejected(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"schema_version": "wrong", "run_type": "SYSTEM_TEST", "candidates": []}), encoding="utf-8")
    try:
        mod.run(p, tmp_path / "out")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "schema_version" in str(exc)
