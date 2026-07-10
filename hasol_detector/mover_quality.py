from __future__ import annotations

import pandas as pd


def add_mover_quality_flags(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if out.empty:
        out["anomaly_reason"] = ""
        out["is_anomaly"] = False
        return out
    out["anomaly_reason"] = ""
    if "prev_close" in out.columns:
        out.loc[out["prev_close"].fillna(0) < 0.5, "anomaly_reason"] += "LOW_PREV_CLOSE;"
    if "return_1d" in out.columns:
        out.loc[out["return_1d"].abs() > 300, "anomaly_reason"] += "EXTREME_RETURN;"
    if "volume" in out.columns:
        out.loc[out["volume"].fillna(0) < 10000, "anomaly_reason"] += "LOW_VOLUME;"
    out["is_anomaly"] = out["anomaly_reason"].astype(str).ne("")
    return out


def add_pre_move_signals(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if out.empty:
        return out
    g = out.groupby("ticker", group_keys=False)
    shifted_volume = g["volume"].shift(1)
    shifted_high = g["high"].shift(1)
    shifted_close = g["close"].shift(1)
    out["prev_5d_avg_volume"] = shifted_volume.rolling(5, min_periods=3).mean().reset_index(level=0, drop=True)
    out["prev_20d_high"] = shifted_high.rolling(20, min_periods=5).max().reset_index(level=0, drop=True)
    out["prev_20d_close_mean"] = shifted_close.rolling(20, min_periods=5).mean().reset_index(level=0, drop=True)
    out["volume_vs_prev5"] = out["volume"] / out["prev_5d_avg_volume"]
    out["prev_20d_momentum_pct"] = (out["prev_close"] / out["prev_20d_close_mean"] - 1.0) * 100.0
    out["near_prev_20d_high_pct"] = (out["prev_close"] / out["prev_20d_high"] - 1.0) * 100.0
    out["quiet_rs_flag"] = (out["prev_20d_momentum_pct"] > 5) & (out["near_prev_20d_high_pct"] > -8)
    out["volume_expansion_flag"] = out["volume_vs_prev5"] >= 2.0
    out["breakout_flag"] = out["close"] > out["prev_20d_high"]
    return out
