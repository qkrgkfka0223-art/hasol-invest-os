from __future__ import annotations
import pandas as pd
import numpy as np
from .config import EVENT_WEIGHTS, HasolConfig

CAP_BONUS = {
    "mega_cap": -5,
    "large_cap": -1,
    "mid_cap": 4,
    "small_cap": 7,
    "micro_cap": 5,
    "nano_cap": -2,
    "unknown": -15,
}

def _event_score(tags: str) -> float:
    if not tags:
        return 0
    return max(EVENT_WEIGHTS.get(t, 0) for t in str(tags).split(";"))

def _has_tag(tags: pd.Series, pattern: str) -> pd.Series:
    return tags.astype(str).str.contains(pattern, regex=True, na=False)

def score_candidates(df: pd.DataFrame, market_code: str = "SOFT_GO", config: HasolConfig | None = None) -> pd.DataFrame:
    config = config or HasolConfig()
    out = df.copy()
    out["event_score"] = out["event_tags"].apply(_event_score)
    out["source_count_score"] = np.log1p(pd.to_numeric(out.get("source_count", 1), errors="coerce").fillna(1)).clip(0, 2.2) * 4
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

    event_tags = out["event_tags"].astype(str)
    out["sec_cluster_score"] = _has_tag(event_tags, "SEC_CLUSTER|OWNERSHIP_CHANGE|COMPLIANCE_RECOVERY").astype(int) * 9
    out["famous_partner_score"] = (out.get("famous_partner_hits", "").astype(str).str.len() > 0).astype(int) * 6
    out["biotech_expansion_score"] = _has_tag(event_tags, "CLINICAL_SUCCESS|BLA_ACCEPTED|BIOTECH_LICENSE").astype(int) * 8
    out["earnings_quality_score"] = _has_tag(event_tags, "EARNINGS|GUIDANCE_RAISE|BACKLOG_INCREASE").astype(int) * 6

    out["watchlist_group_score"] = 0
    group = out.get("watchlist_group", "").astype(str)
    out.loc[group.str.contains("A", na=False), "watchlist_group_score"] += 8
    out.loc[group.str.contains("B", na=False), "watchlist_group_score"] += 5
    out.loc[group.str.contains("C", na=False), "watchlist_group_score"] -= 8
    out.loc[group.str.contains("D", na=False), "watchlist_group_score"] -= 25

    out["micro_nano_detect_bonus"] = 0
    micro_nano = out["cap_bucket"].isin(["micro_cap", "nano_cap"])
    out.loc[micro_nano & (out["event_score"] >= 12) & (out["relative_volume"].fillna(0) >= 2), "micro_nano_detect_bonus"] += 8
    out.loc[micro_nano & _has_tag(event_tags, "SEC_CLUSTER|COMPLIANCE_RECOVERY|FAMOUS_PARTNER|AI_INFRA|SPACE"), "micro_nano_detect_bonus"] += 5

    out["cap_bucket_bonus"] = out["cap_bucket"].map(CAP_BONUS).fillna(-10)
    out["market_score"] = {"GO": 8, "SOFT_GO": 3, "NO_TRADE": -25}.get(market_code, 0)

    overheat = (
        out["parabolic_3d_flag"].fillna(False).astype(bool).astype(int) * 12 +
        (out["climax_volume_flag"].fillna(False).astype(bool) & (out["change_pct"] > 20)).astype(int) * 10 +
        out["long_upper_wick_flag"].fillna(False).astype(bool).astype(int) * 6 +
        (out["change_pct"] > 60).astype(int) * 16 +
        (out["post_spike_stage"].astype(str).isin(["day3_parabolic", "post_climax_fade"])).astype(int) * 10
    )
    out["overheat_penalty"] = overheat

    txt = out.get("headline", pd.Series([""] * len(out))).fillna("").str.lower()
    out["dilution_penalty"] = txt.str.contains("offering|registered direct|warrant|atm", regex=True).astype(int) * 15
    out["bad_news_penalty"] = txt.str.contains("investigation|delisting|bankruptcy|going concern|halt|probe", regex=True).astype(int) * 20
    out["bad_event_penalty"] = out.get("bad_event_flag", False).fillna(False).astype(bool).astype(int) * 25
    out["stale_news_penalty"] = 0
    if "headline_age_days" in out.columns:
        out.loc[(pd.to_numeric(out["headline_age_days"], errors="coerce") > config.stale_news_days) & (out["change_pct"] > 20), "stale_news_penalty"] += 10

    out["data_quality_penalty"] = 0
    if "data_quality_status" in out.columns:
        out.loc[out["data_quality_status"].astype(str).str.contains("MISSING_MARKET_CAP|MISSING_PRICE", regex=True), "data_quality_penalty"] += 20
        out.loc[out["data_quality_status"].astype(str).str.contains("INSUFFICIENT_HISTORY", regex=True), "data_quality_penalty"] += 8
        out.loc[out["data_quality_status"].astype(str).str.contains("SAMPLE_MODE", regex=True), "data_quality_penalty"] += 0

    out["total_score"] = (
        out["market_score"] + out["event_score"] + out["source_count_score"] + out["rs_score"] + out["volume_score"] +
        out["price_score"] + out["underreaction_score"] + out["cap_bucket_bonus"] + out["watchlist_group_score"] +
        out["sec_cluster_score"] + out["famous_partner_score"] + out["biotech_expansion_score"] + out["earnings_quality_score"] + out["micro_nano_detect_bonus"] -
        out["overheat_penalty"] - out["dilution_penalty"] - out["bad_news_penalty"] - out["bad_event_penalty"] - out["stale_news_penalty"] - out["data_quality_penalty"]
    ).round(2)

    out["detect_only_reason"] = ""
    out.loc[out["cap_bucket"].isin(["micro_cap", "nano_cap"]), "detect_only_reason"] = "MICRO_NANO_DETECT_ONLY"
    out.loc[out["post_spike_stage"].isin(["day2_continuation", "day3_parabolic", "post_climax_fade"]), "detect_only_reason"] = out["detect_only_reason"].mask(out["detect_only_reason"].eq(""), "POST_SPIKE_REVIEW_ONLY")
    out.loc[out.get("source_confidence", "").astype(str).str.contains("BIOTECH_LOCKED", regex=False, na=False), "detect_only_reason"] = out["detect_only_reason"].mask(out["detect_only_reason"].eq(""), "BIOTECH_WEB_VALIDATION_LOCK")
    out.loc[out.get("bad_event_flag", False).fillna(False).astype(bool), "detect_only_reason"] = out["detect_only_reason"].mask(out["detect_only_reason"].eq(""), "BAD_EVENT_REVIEW_LOCK")
    out.loc[group.str.contains("C", na=False), "detect_only_reason"] = out["detect_only_reason"].mask(out["detect_only_reason"].eq(""), "C_GROUP_REVIEW_ONLY")
    out.loc[group.str.contains("D", na=False), "detect_only_reason"] = out["detect_only_reason"].mask(out["detect_only_reason"].eq(""), "D_GROUP_EXECUTION_BAN")
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
    group = top5.get("watchlist_group", "").astype(str)
    allowed = top5.get("execution_allowed", "").astype(str).str.lower()
    event_ok = top5["event_tags"].astype(str).ne("NONE")
    watchlist_ok = group.str.contains("A|B", regex=True, na=False) & allowed.isin(["yes", "conditional"])
    ok = (
        watchlist_ok &
        event_ok &
        (top5["change_pct"] < 25) &
        (top5["relative_volume"] < 8) &
        (~top5["parabolic_3d_flag"].fillna(False)) &
        (~top5["climax_volume_flag"].fillna(False)) &
        (~top5["is_chase_risk"].fillna(False)) &
        (~top5["cap_bucket"].isin(["micro_cap", "nano_cap", "unknown"])) &
        (~top5.get("bad_event_flag", False).fillna(False)) &
        (top5["above_ma20"].fillna(False)) &
        (top5["market_cap"].fillna(0) >= 300_000_000) &
        (~top5.get("missing_price", False)) &
        (~top5.get("missing_market_cap", False))
    )
    out = top5[ok].copy()
    out["execution_reason"] = "live mode, A/B watchlist, event-tagged, web review still required, no chase flags, non-micro/nano, trend support maintained"
    out["execution_lock_reason"] = "MANUAL_REVIEW_REQUIRED"
    return out
