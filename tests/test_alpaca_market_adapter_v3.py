from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone

import pytest

from hasol_runtime.adapters.alpaca_market import build_market_snapshot


CUTOFF = "2026-08-19T16:00:00-04:00"


def business_days(end: date, count: int) -> list[date]:
    days: list[date] = []
    current = end
    while len(days) < count:
        if current.weekday() < 5:
            days.append(current)
        current -= timedelta(days=1)
    return sorted(days)


def make_assets(n: int = 2):
    return [
        {
            "symbol": f"T{i:02d}",
            "exchange": "NASDAQ",
            "class": "us_equity",
            "status": "active",
            "security_type": "COMMON_STOCK",
            "classification_source": "TEST_SECURITY_MASTER",
            "excluded_security_flag": False,
        }
        for i in range(n)
    ]


def make_bars(symbol: str, session_count: int = 21):
    sessions = business_days(date(2026, 8, 19), session_count)
    out = []
    for i, session in enumerate(sessions):
        # Alpaca 1Day bars are observed with UTC timestamps near midnight ET.
        ts = datetime.combine(session, time(4, 0), tzinfo=timezone.utc)
        out.append({
            "symbol": symbol,
            "timestamp": ts.isoformat(),
            "close": 10.0 + i,
            "volume": 1_000_000.0 + i,
        })
    return out


def make_payload(n: int = 2):
    assets = make_assets(n)
    bars = {asset["symbol"]: make_bars(asset["symbol"]) for asset in assets}
    return assets, {"bars": bars}


def build(assets, bars):
    return build_market_snapshot(
        assets=assets,
        bars_payload=bars,
        cutoff_et=CUTOFF,
        source_ref="alpaca://sip/2026-08-19-close",
        feed="sip",
    )


def test_adv20_excludes_cutoff_session():
    assets, bars = make_payload(1)
    snap = build(assets, bars)
    row = snap["rows"][0]
    assert row["cutoff_session"] == "2026-08-19"
    assert row["adv20_excludes_cutoff_session"] is True
    assert len(row["adv20_sessions"]) == 20
    assert "2026-08-19" not in row["adv20_sessions"]

    prior = bars["bars"]["T00"][:-1]
    expected = sum(float(b["close"]) * float(b["volume"]) for b in prior[-20:]) / 20
    assert row["adv20_usd"] == round(expected, 8)


def test_same_input_produces_same_snapshot_hash():
    assets, bars = make_payload(2)
    first = build(assets, bars)
    second = build(deepcopy(assets), deepcopy(bars))
    assert first["snapshot_hash"] == second["snapshot_hash"]
    assert first["rows"] == second["rows"]


def test_future_bar_rejected():
    assets, bars = make_payload(1)
    bars["bars"]["T00"].append({
        "symbol": "T00",
        "timestamp": "2026-08-20T04:00:00+00:00",
        "close": 31.0,
        "volume": 1_000_000,
    })
    with pytest.raises(ValueError, match="future bar"):
        build(assets, bars)


def test_duplicate_session_rejected():
    assets, bars = make_payload(1)
    duplicate = deepcopy(bars["bars"]["T00"][0])
    duplicate["timestamp"] = duplicate["timestamp"].replace("04:00:00", "05:00:00")
    bars["bars"]["T00"].append(duplicate)
    with pytest.raises(ValueError, match="duplicate daily bar"):
        build(assets, bars)


def test_insufficient_prior_sessions_not_fabricated():
    assets = make_assets(1)
    bars = {"bars": {"T00": make_bars("T00", session_count=20)}}
    snap = build(assets, bars)
    assert snap["rows"] == []
    assert snap["insufficient_history"] == ["T00"]
    assert snap["coverage"] == 0.0


def test_nonfinite_market_value_rejected():
    assets, bars = make_payload(1)
    bars["bars"]["T00"][0]["close"] = float("nan")
    with pytest.raises(ValueError, match="must be finite"):
        build(assets, bars)


def test_common_stock_classification_source_is_mandatory():
    assets, bars = make_payload(1)
    del assets[0]["classification_source"]
    with pytest.raises(ValueError, match="classification_source missing"):
        build(assets, bars)


def test_non_common_and_unsupported_exchange_are_excluded():
    assets, bars = make_payload(2)
    assets[0]["security_type"] = "ETF"
    assets[1]["exchange"] = "ARCA"
    with pytest.raises(ValueError, match="classified asset universe is empty"):
        build(assets, bars)
