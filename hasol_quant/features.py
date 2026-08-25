from __future__ import annotations

import numpy as np
import pandas as pd

from .config import FEATURE_SPEC_VERSION


def _safe_return(closes: pd.Series, periods: int) -> float:
    closes = pd.to_numeric(closes, errors="coerce").dropna()
    if len(closes) <= periods:
        return np.nan
    base = closes.iloc[-periods - 1]
    last = closes.iloc[-1]
    if not np.isfinite(base) or base == 0:
        return np.nan
    return float(last / base - 1.0)


def _atr(g: pd.DataFrame, window: int) -> float:
    if len(g) < 2:
        return np.nan
    high = pd.to_numeric(g["high"], errors="coerce")
    low = pd.to_numeric(g["low"], errors="coerce")
    close = pd.to_numeric(g["close"], errors="coerce")
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return float(tr.tail(window).mean()) if not tr.dropna().empty else np.nan


def _ema_last(closes: pd.Series, span: int) -> float:
    closes = pd.to_numeric(closes, errors="coerce").dropna()
    return float(closes.ewm(span=span, adjust=False).mean().iloc[-1]) if not closes.empty else np.nan


def _one_ticker(g: pd.DataFrame) -> pd.Series:
    g = g.sort_values("timestamp").reset_index(drop=True)
    closes = pd.to_numeric(g["close"], errors="coerce")
    vols = pd.to_numeric(g["volume"], errors="coerce")
    last = g.iloc[-1]
    prev = g.iloc[-2] if len(g) >= 2 else last
    dollar = closes * vols
    prior_vol20 = vols.iloc[-21:-1] if len(vols) >= 21 else vols.iloc[:-1].tail(20)
    last20_dollar = dollar.tail(20)
    avg_vol20 = prior_vol20.mean() if len(prior_vol20) else np.nan
    vol_std20 = prior_vol20.std(ddof=1) if len(prior_vol20) >= 2 else np.nan
    high20 = pd.to_numeric(g["high"], errors="coerce").tail(20).max()
    high60 = pd.to_numeric(g["high"], errors="coerce").tail(60).max()
    prev_high20 = pd.to_numeric(g["high"], errors="coerce").iloc[:-1].tail(20).max()
    close = float(last["close"])
    prev_close = float(prev["close"]) if pd.notna(prev["close"]) else np.nan
    atr14, atr5, atr20 = _atr(g, 14), _atr(g, 5), _atr(g, 20)
    ema20 = _ema_last(closes, 20)
    day_range = float(last["high"] - last["low"]) if pd.notna(last["high"]) and pd.notna(last["low"]) else np.nan
    close_location = float((last["close"] - last["low"]) / day_range) if pd.notna(day_range) and day_range > 0 else np.nan
    return pd.Series({
        "feature_spec_version": FEATURE_SPEC_VERSION,
        "as_of_timestamp": last["timestamp"],
        "history_bars": int(len(g)),
        "open": float(last["open"]), "high": float(last["high"]), "low": float(last["low"]), "close": close,
        "volume": float(last["volume"]),
        "trade_count": float(last["trade_count"]) if pd.notna(last.get("trade_count")) else np.nan,
        "vwap": float(last["vwap"]) if pd.notna(last.get("vwap")) else np.nan,
        "ret_1d": _safe_return(closes, 1), "ret_3d": _safe_return(closes, 3), "ret_5d": _safe_return(closes, 5),
        "ret_10d": _safe_return(closes, 10), "ret_20d": _safe_return(closes, 20), "ret_60d": _safe_return(closes, 60),
        "adv20_usd": float(last20_dollar.mean()) if len(last20_dollar) else np.nan,
        "vol_ratio20": float(last["volume"] / avg_vol20) if pd.notna(avg_vol20) and avg_vol20 > 0 else np.nan,
        "vol_z20": float((last["volume"] - avg_vol20) / vol_std20) if pd.notna(vol_std20) and vol_std20 > 0 else np.nan,
        "gap_pct": float(last["open"] / prev_close - 1.0) if pd.notna(prev_close) and prev_close != 0 else np.nan,
        "close_location": close_location,
        "atr14_pct": float(atr14 / close) if pd.notna(atr14) and close else np.nan,
        "compression": float(atr5 / atr20) if pd.notna(atr5) and pd.notna(atr20) and atr20 > 0 else np.nan,
        "dist_high20": float(close / high20 - 1.0) if pd.notna(high20) and high20 else np.nan,
        "dist_high60": float(close / high60 - 1.0) if pd.notna(high60) and high60 else np.nan,
        "breakout20": float(close / prev_high20 - 1.0) if pd.notna(prev_high20) and prev_high20 else np.nan,
        "ema20_extension": float(close / ema20 - 1.0) if pd.notna(ema20) and ema20 else np.nan,
    })


def build_features(bars_df: pd.DataFrame) -> pd.DataFrame:
    required = {"ticker", "timestamp", "open", "high", "low", "close", "volume"}
    missing = required - set(bars_df.columns)
    if missing:
        raise ValueError(f"Missing required bar columns: {sorted(missing)}")
    if bars_df.empty:
        return pd.DataFrame()
    x = bars_df.copy()
    x["ticker"] = x["ticker"].astype(str).str.upper()
    x["timestamp"] = pd.to_datetime(x["timestamp"], utc=True, errors="coerce")
    x = x.dropna(subset=["ticker", "timestamp", "close"]).sort_values(["ticker", "timestamp"])
    rows = []
    for ticker, g in x.groupby("ticker", sort=True):
        row = _one_ticker(g)
        row["ticker"] = ticker
        rows.append(row)
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    bench = out.set_index("ticker")
    for horizon in (5, 20, 60):
        spy = bench.loc["SPY", f"ret_{horizon}d"] if "SPY" in bench.index else np.nan
        out[f"rs_{horizon}d_spy"] = out[f"ret_{horizon}d"] - spy
    return out
