from __future__ import annotations
import pandas as pd
from .config import HasolConfig


def apply_kill_rules(df: pd.DataFrame, market_code: str = "SOFT_GO", config: HasolConfig | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    config = config or HasolConfig()
    out = df.copy()
    reasons = []
    for _, r in out.iterrows():
        rs = []
        if market_code == "NO_TRADE":
            rs.append("NO_TRADE 시장")
        if float(r.get("price", 0) or 0) < config.min_price:
            rs.append("가격 기준 미달")
        if float(r.get("dollar_volume", 0) or 0) < config.min_dollar_volume:
            rs.append("거래대금 부족")
        if r.get("cap_bucket") == "nano_cap" and float(r.get("change_pct", 0) or 0) > 25:
            rs.append("초저시총 급등 추격 위험")
        if float(r.get("change_pct", 0) or 0) > 70:
            rs.append("당일 급등 과열")
        if bool(r.get("parabolic_3d_flag", False)):
            rs.append("3일 포물선")
        if bool(r.get("climax_volume_flag", False)) and (float(r.get("relative_volume", 0) or 0) > 10) and (float(r.get("change_pct", 0) or 0) > 20):
            rs.append("거래량 클라이맥스")
        if bool(r.get("long_upper_wick_flag", False)) and float(r.get("change_pct", 0) or 0) > 15:
            rs.append("긴 윗꼬리")
        if r.get("cap_bucket") == "unknown":
            rs.append("시총 미확인")
        reasons.append("; ".join(rs))
    out["reject_reason"] = reasons
    rejected = out[out["reject_reason"] != ""].copy()
    kept = out[out["reject_reason"] == ""].copy()
    return kept.sort_values("total_score", ascending=False), rejected.sort_values("total_score", ascending=False)
