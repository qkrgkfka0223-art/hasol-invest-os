from __future__ import annotations
import pandas as pd
from .config import HasolConfig


def apply_kill_rules(df: pd.DataFrame, market_code: str = "SOFT_GO", config: HasolConfig | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    config = config or HasolConfig()
    out = df.copy()
    reasons = []
    review_locks = []
    for _, r in out.iterrows():
        rs = []
        locks = []
        if market_code == "NO_TRADE":
            rs.append("NO_TRADE 시장")
        if float(r.get("price", 0) or 0) < config.min_price:
            rs.append("가격 기준 미달")
        if float(r.get("dollar_volume", 0) or 0) < config.min_dollar_volume:
            rs.append("거래대금 부족")
        if r.get("cap_bucket") == "unknown":
            rs.append("시총 미확인")

        if r.get("cap_bucket") in ["micro_cap", "nano_cap"]:
            locks.append("MICRO_NANO_EXECUTION_LOCK")
        if r.get("post_spike_stage") in ["day2_continuation", "day3_parabolic", "post_climax_fade"]:
            locks.append("POST_SPIKE_REVIEW_ONLY")
        if float(r.get("change_pct", 0) or 0) > 70:
            locks.append("당일 급등 과열")
        if bool(r.get("parabolic_3d_flag", False)):
            locks.append("3일 포물선")
        if bool(r.get("climax_volume_flag", False)) and (float(r.get("relative_volume", 0) or 0) > 10) and (float(r.get("change_pct", 0) or 0) > 20):
            locks.append("거래량 클라이맥스")
        if bool(r.get("long_upper_wick_flag", False)) and float(r.get("change_pct", 0) or 0) > 15:
            locks.append("긴 윗꼬리")
        if str(r.get("headline", "")).lower().find("offering") >= 0:
            locks.append("offering 확인 필요")
        if str(r.get("headline", "")).lower().find("delisting") >= 0:
            locks.append("delisting 확인 필요")

        reasons.append("; ".join(rs))
        review_locks.append("; ".join(locks))

    out["reject_reason"] = reasons
    out["review_lock_reason"] = review_locks
    rejected = out[out["reject_reason"] != ""].copy()
    kept = out[out["reject_reason"] == ""].copy()
    return kept.sort_values("total_score", ascending=False), rejected.sort_values("total_score", ascending=False)
