from __future__ import annotations
import pandas as pd
from .config import HasolConfig


def bucket_for_cap(market_cap, config: HasolConfig) -> str:
    try:
        cap = float(market_cap)
    except Exception:
        return "unknown"
    if pd.isna(cap):
        return "unknown"
    for rule in config.cap_rules:
        if cap >= rule.min_cap and cap < rule.max_cap:
            return rule.name
    return "unknown"


def add_cap_bucket(df: pd.DataFrame, config: HasolConfig) -> pd.DataFrame:
    out = df.copy()
    out["cap_bucket"] = out["market_cap"].apply(lambda x: bucket_for_cap(x, config))
    return out


def select_top20_by_cap_bucket(df: pd.DataFrame, config: HasolConfig, score_col: str = "total_score") -> pd.DataFrame:
    """Select Top20 with hard cap-bucket quotas.

    If fewer than 20 candidates pass quotas, return fewer rows rather than allowing
    large/liquid names to dominate again.
    """
    if df.empty:
        out = df.copy()
        out["top20_rank"] = []
        return out

    ranked = df.sort_values(score_col, ascending=False).copy()
    selected = []
    used = set()

    for bucket, quota in config.top20_quotas.items():
        if quota <= 0:
            continue
        b = ranked[(ranked["cap_bucket"] == bucket) & (~ranked["ticker"].isin(used))].head(quota)
        if not b.empty:
            selected.append(b)
            used.update(b["ticker"].astype(str).tolist())

    if selected:
        out = pd.concat(selected, ignore_index=True).sort_values(score_col, ascending=False).head(20).copy()
    else:
        out = ranked.head(20).copy()

    out["top20_rank"] = range(1, len(out) + 1)
    return out
