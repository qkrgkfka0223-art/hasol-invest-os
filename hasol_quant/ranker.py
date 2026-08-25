from __future__ import annotations

import numpy as np
import pandas as pd

from .config import RANK_SPEC_VERSION

RANK_WEIGHTS = {
    "rs_5d_spy": 0.15, "rs_20d_spy": 0.15, "rs_60d_spy": 0.15,
    "vol_z20": 0.08, "vol_ratio20": 0.06, "close_location": 0.06, "breakout20": 0.05,
    "compression_inv": 0.06, "near_high20": 0.07, "ret_20d": 0.04, "ret_5d": 0.03,
}


def _pct_rank(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").rank(pct=True, method="average", ascending=True)


def _risk_penalty(row: pd.Series) -> float:
    penalty = 0.0
    ext, gap, ret3, volz, loc = row.get("ema20_extension"), row.get("gap_pct"), row.get("ret_3d"), row.get("vol_z20"), row.get("close_location")
    if pd.notna(ext) and ext > 0.20: penalty += min(20.0, (float(ext) - 0.20) * 100.0)
    if pd.notna(gap) and gap > 0.12: penalty += min(15.0, (float(gap) - 0.12) * 100.0)
    if pd.notna(ret3) and ret3 > 0.45: penalty += 15.0
    if pd.notna(volz) and volz > 5 and pd.notna(loc) and loc < 0.60: penalty += 10.0
    return float(min(40.0, penalty))


def rank_universe(features_df: pd.DataFrame, eligible_tickers: set[str] | None = None) -> pd.DataFrame:
    x = features_df.copy()
    if eligible_tickers is not None:
        x = x[x["ticker"].isin(eligible_tickers)].copy()
    if x.empty:
        return x
    x["compression_inv"] = -pd.to_numeric(x["compression"], errors="coerce")
    x["near_high20"] = pd.to_numeric(x["dist_high20"], errors="coerce")
    weighted_sum = pd.Series(0.0, index=x.index)
    weight_sum = pd.Series(0.0, index=x.index)
    valid_signals = pd.Series(0, index=x.index, dtype=int)
    for col, weight in RANK_WEIGHTS.items():
        p = _pct_rank(x[col])
        x[f"pct_{col}"] = p
        mask = p.notna()
        weighted_sum.loc[mask] += p.loc[mask] * weight
        weight_sum.loc[mask] += weight
        valid_signals.loc[mask] += 1
    x["signal_count"] = valid_signals
    x["quant_raw_score"] = np.where(weight_sum > 0, weighted_sum / weight_sum * 100.0, np.nan)
    x["risk_penalty"] = x.apply(_risk_penalty, axis=1)
    x["quant_score"] = x["quant_raw_score"] - x["risk_penalty"]
    x.loc[x["signal_count"] < 6, "quant_score"] = np.nan
    x["rank_spec_version"] = RANK_SPEC_VERSION
    x = x.sort_values(["quant_score", "adv20_usd", "ticker"], ascending=[False, False, True], na_position="last").reset_index(drop=True)
    x["quant_rank"] = np.arange(1, len(x) + 1)
    return x


def top_n(ranked_df: pd.DataFrame, n: int = 50) -> pd.DataFrame:
    return ranked_df[ranked_df["quant_score"].notna()].head(n).copy()
