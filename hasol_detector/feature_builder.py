from __future__ import annotations
import pandas as pd
import numpy as np

def _return_n(closes: pd.Series, n: int) -> float:
    if len(closes) <= 1:
        return 0.0
    idx = -min(n + 1, len(closes))
    base = closes.iloc[idx]
    if not base:
        return 0.0
    return (closes.iloc[-1] / base - 1) * 100

def _benchmark_5d(history_df: pd.DataFrame, ticker: str, fallback: float) -> float:
    if history_df.empty or "ticker" not in history_df.columns:
        return fallback
    h = history_df[history_df["ticker"].astype(str).str.upper() == ticker].sort_values("date")
    if h.empty:
        return fallback
    closes = pd.to_numeric(h["close"], errors="coerce").dropna()
    return _return_n(closes, 5) if len(closes) > 1 else fallback

def build_features(profile_df: pd.DataFrame, history_df: pd.DataFrame) -> pd.DataFrame:
    h = history_df.copy()
    h["date"] = pd.to_datetime(h["date"], errors="coerce")
    h = h.dropna(subset=["date", "ticker", "close"]).sort_values(["ticker", "date"])

    def last_features(g: pd.DataFrame) -> pd.Series:
        closes = pd.to_numeric(g["close"], errors="coerce").dropna()
        vols = pd.to_numeric(g["volume"], errors="coerce").fillna(0)
        last = g.iloc[-1]
        prev = g.iloc[-2] if len(g) >= 2 else last
        ma20 = closes.tail(20).mean() if len(closes) else np.nan
        ma50 = closes.tail(50).mean() if len(closes) else np.nan
        avg_vol20 = vols.tail(20).mean() if len(vols) else np.nan
        high_low = max(0.01, float(last["high"] - last["low"])) if pd.notna(last.get("high")) and pd.notna(last.get("low")) else 0.01
        upper_range = (float(last["high"]) - max(float(last["open"]), float(last["close"]))) / high_low if pd.notna(last.get("high")) else 0
        three_day = closes.tail(3)
        parabolic_3d = len(three_day) == 3 and (three_day.iloc[-1] / three_day.iloc[0] - 1) > 0.45
        climax_volume = bool(avg_vol20 and float(last["volume"]) > avg_vol20 * 6)
        latest_bar_date = pd.to_datetime(last["date"]).date().isoformat() if pd.notna(last["date"]) else ""
        return pd.Series({
            "open": float(last["open"]),
            "high": float(last["high"]),
            "low": float(last["low"]),
            "close": float(last["close"]),
            "volume": float(last["volume"]),
            "history_bars": int(len(g)),
            "latest_bar_date": latest_bar_date,
            "avg_volume_20d": float(avg_vol20) if pd.notna(avg_vol20) else np.nan,
            "ma20": float(ma20) if pd.notna(ma20) else np.nan,
            "ma50": float(ma50) if pd.notna(ma50) else np.nan,
            "return_1d": (float(last["close"]) / float(prev["close"]) - 1) * 100 if prev["close"] else 0,
            "return_3d": _return_n(closes, 3),
            "return_5d": _return_n(closes, 5),
            "return_20d": _return_n(closes, 20),
            "above_ma20": bool(float(last["close"]) > ma20) if pd.notna(ma20) else False,
            "above_ma50": bool(float(last["close"]) > ma50) if pd.notna(ma50) else False,
            "relative_volume": float(last["volume"] / avg_vol20) if avg_vol20 and pd.notna(avg_vol20) else np.nan,
            "dollar_volume": float(last["close"] * last["volume"]),
            "long_upper_wick_flag": bool(upper_range > 0.45),
            "parabolic_3d_flag": bool(parabolic_3d),
            "climax_volume_flag": bool(climax_volume),
            "gap_pct": (float(last["open"]) / float(prev["close"]) - 1) * 100 if prev["close"] else 0,
        })

    features = h.groupby("ticker", group_keys=False).apply(last_features).reset_index()
    out = profile_df.merge(features, on="ticker", how="left")
    out["price"] = pd.to_numeric(out.get("close", out.get("price")), errors="coerce").fillna(pd.to_numeric(out.get("price"), errors="coerce"))
    out["prev_close"] = pd.to_numeric(out["prev_close"], errors="coerce")
    out["change_pct"] = (out["price"] / out["prev_close"] - 1) * 100

    spy_5d = _benchmark_5d(h, "SPY", 1.8)
    qqq_5d = _benchmark_5d(h, "QQQ", 2.2)
    out["benchmark_spy_5d"] = spy_5d
    out["benchmark_qqq_5d"] = qqq_5d
    out["spy_relative_5d"] = out["return_5d"].fillna(0) - spy_5d
    out["qqq_relative_5d"] = out["return_5d"].fillna(0) - qqq_5d
    out["volume_acceleration"] = out["relative_volume"].fillna(0)
    return out
