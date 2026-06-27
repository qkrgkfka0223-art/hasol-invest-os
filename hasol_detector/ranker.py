from __future__ import annotations
import pandas as pd
import numpy as np
from .config import EVENT_WEIGHTS, HasolConfig

CAP_BONUS = {
    "mega_cap": -5,
    "large_cap": -1,
    "mid_cap": 4,
    "small_cap": 7,
    "micro_cap": 3,
    "nano_cap": -12,
    "unknown": -15,
}

def _event_score(tags: str) -> float:
    if not tags:
        return 0
    return max(EVENT_WEIGHTS.get(t, 0) for t in str(tags).split(";"))

def score_candidates(df: pd.DataFrame, market_code: str = "SOFT_GO", config: HasolConfig | None = None) -> pd.DataFrame:
    config = config or HasolConfig()
    out = df.copy()
    out["event_score"] = out["event_tags"].apply(_event_score)
    out["rs_score"] = out[["spy_relative_5d", "qqq_relative_5d"]].mean(axis=1).clip(-20, 25) * 0.8
    out["volume_score"] = np.log1p(out["relative_volume"].fillna(0)).clip(0, 3) * 6
    out["price_score"] = 0
    out.loc[out["above_ma20"].fillna(False), "price_score"] += 5
    out.loc[out["above_ma50"].fillna(False), "price_score"] += 4
    out.loc[out["change_pct"].between(2, 20), "price_score"] += 6
    out.loc[out["change_pct"].between(20, 40), "price_score"] += 2
    out.loc[out["change_pct"] > 40, "price_score"] -= 8

    out["underreaction_score"] = 0
    strong_event = out["event_score"] >= 12
    out.loc[strong_event & out["change_pct"].between(-2, 18), "underreaction_score"] += 10
    out.loc[strong_event & out["change_pct"].between(18, 35), "underreaction_score"] += 4
    out.loc[strong_event & (out["change_pct"] > 50), "underreaction_score"] -= 10

    out["cap_bucket_bonus"] = out["cap_bucket"].map(CAP_BONUS).fillna(-10)
    out["market_score"] = {"GO": 8, "SOFT_GO": 3, "NO_TRADE": -25}.get(market_code, 0)

    overheat = (
        out["parabolic_3d_flag"].fillna(False).astype(bool).astype(int) * 12 +
        (out["climax_volume_flag"].fillna(False).astype(bool) & (out["change_pct"] > 20)).astype(int) * 10 +
        out["long_upper_wick_flag"].fillna(False).astype(bool).astype(int) * 6 +
        (out["change_pct"] > 60).astype(int) * 16 +
        (out["cap_bucket"].isin(["nano_cap"]) & (out["change_pct"] > 25)).astype(int) * 10
    )
    out["overheat_penalty"] = overheat

    txt = out.get("headline", pd.Series([""] * len(out))).fillna("").str.lower()
    out["dilution_penalty"] = txt.str.contains("offering|registered direct|warrant|atm", regex=True).astype(int) * 15
    out["bad_news_penalty"] = txt.str.contains("investigation|delisting|bankruptcy|going concern", regex=True).astype(int) * 20
    out["data_quality_penalty"] = 0
    if "data_quality_status" in out.columns:
        out.loc[out["data_quality_status"].astype(str).str.contains("MISSING_MARKET_CAP|MISSING_PRICE", regex=True), "data_quality_penalty"] += 20
        out.loc[out["data_quality_status"].astype(str).str.contains("INSUFFICIENT_HISTORY", regex=True), "data_quality_penalty"] += 8
        out.loc[out["data_quality_status"].astype(str).str.contains("SAMPLE_MODE", regex=True), "data_quality_penalty"] += 0

    out["total_score"] = (
        out["market_score"] + out["event_score"] + out["rs_score"] + out["volume_score"] +
        out["price_score"] + out["underreaction_score"] + out["cap_bucket_bonus"] -
        out["overheat_penalty"] - out["dilution_penalty"] - out["bad_news_penalty"] - out["data_quality_penalty"]
    ).round(2)
    return out.sort_values("total_score", ascending=False)

def select_top5(top20: pd.DataFrame) -> pd.DataFrame:
    out = top20.sort_values("total_score", ascending=False).head(5).copy()
    out["top5_rank"] = range(1, len(out) + 1)
    return out

def select_execution_candidates(top5: pd.DataFrame, market_code: str = "SOFT_GO", data_mode: str = "sample", allow_execution: bool = False) -> pd.DataFrame:
    cols = list(top5.columns) + ["execution_reason", "execution_lock_reason"] if not top5.empty else ["ticker", "execution_reason", "execution_lock_reason"]
    if not allow_execution:
        return pd.DataFrame(columns=cols)
    if data_mode != "live":
        return pd.DataFrame(columns=cols)
    if market_code == "NO_TRADE":
        return pd.DataFrame(columns=cols)
    ok = (
        (top5["change_pct"] < 25) &
        (top5["relative_volume"] < 8) &
        (~top5["parabolic_3d_flag"].fillna(False)) &
        (~top5["climax_volume_flag"].fillna(False)) &
        (top5["above_ma20"].fillna(False)) &
        (top5["market_cap"].fillna(0) >= 50_000_000) &
        (~top5.get("missing_price", False)) &
        (~top5.get("missing_market_cap", False))
    )
    out = top5[ok].copy()
    out["execution_reason"] = "event+RS 유지, 과열 플래그 없음, 무효선 계산 가능, live mode manual unlock"
    out["execution_lock_reason"] = "UNLOCKED_BY_FLAG_REQUIRES_HARAM_APPROVAL"
    return out
