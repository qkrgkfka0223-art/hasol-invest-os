from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import run_web_candidate_quant as mod


def _bars() -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2026-04-01", periods=80, freq="B", tz="UTC")
    for ticker, base, vol in [("AAA", 20.0, 1_500_000), ("BBB", 8.0, 2_000_000), ("SPY", 500.0, 50_000_000)]:
        for i, ts in enumerate(dates):
            close = base * (1 + i * (0.002 if ticker == "AAA" else 0.0008))
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


def test_candidate_quant_is_deterministic_and_noncanonical(tmp_path: Path, monkeypatch) -> None:
    payload = {
        "schema_version": "HASOL-WEB-CANDIDATES-v1",
        "run_type": "SYSTEM_TEST",
        "eligible_for_prediction": False,
        "prediction_date_et": "2026-08-26",
        "candidates": [
            {"ticker": "AAA", "event_id": "E1", "event_type": "CONTRACT"},
            {"ticker": "BBB", "event_id": "E2", "event_type": "FDA"},
        ],
    }
    source = tmp_path / "input.json"
    source.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(mod, "fetch_daily_bars", lambda *args, **kwargs: _bars())

    out1, out2 = tmp_path / "o1", tmp_path / "o2"
    m1 = mod.run(source, out1)
    m2 = mod.run(source, out2)

    assert m1["quant_market_source"] == "YAHOO_YFINANCE_DETECTION_ONLY"
    assert m1["quant_source_policy"] == "DETECTION_ONLY_NOT_CANONICAL"
    assert m1["final_market_validator"] == "ALPACA_CONNECTED_APP"
    assert m1["input_sha256"] == m2["input_sha256"]
    a = pd.read_csv(out1 / "web_candidate_quant.csv")
    b = pd.read_csv(out2 / "web_candidate_quant.csv")
    pd.testing.assert_frame_equal(a, b)
    assert set(a["ticker"]) == {"AAA", "BBB"}
    assert (out1 / "quant_top50.json").exists()
    assert (out1 / "data_quality.json").exists()


def test_invalid_schema_rejected(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"schema_version": "wrong", "candidates": []}), encoding="utf-8")
    try:
        mod.run(p, tmp_path / "out")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "schema_version" in str(exc)
