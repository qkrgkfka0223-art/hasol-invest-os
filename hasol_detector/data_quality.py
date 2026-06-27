from __future__ import annotations
import pandas as pd
from .config import HasolConfig

def add_data_quality_flags(df: pd.DataFrame, data_mode: str, config: HasolConfig) -> pd.DataFrame:
    out = df.copy()
    out["missing_market_cap"] = pd.to_numeric(out.get("market_cap"), errors="coerce").isna()
    out["insufficient_history"] = pd.to_numeric(out.get("history_bars"), errors="coerce").fillna(0) < config.min_history_bars
    out["missing_price"] = pd.to_numeric(out.get("price"), errors="coerce").isna()
    out["sample_mode_lock"] = data_mode == "sample"

    status = []
    for _, r in out.iterrows():
        issues = []
        if bool(r.get("sample_mode_lock", False)):
            issues.append("SAMPLE_MODE")
        if bool(r.get("missing_price", False)):
            issues.append("MISSING_PRICE")
        if bool(r.get("missing_market_cap", False)):
            issues.append("MISSING_MARKET_CAP")
        if bool(r.get("insufficient_history", False)):
            issues.append("INSUFFICIENT_HISTORY")
        status.append("OK" if not issues else ";".join(issues))
    out["data_quality_status"] = status
    return out

def build_run_metadata(raw: pd.DataFrame, scored: pd.DataFrame, top20: pd.DataFrame, top5: pd.DataFrame, data_mode: str, market_code: str, allow_execution: bool) -> dict:
    def dist(frame: pd.DataFrame, col: str) -> dict:
        if frame is None or frame.empty or col not in frame.columns:
            return {}
        return {str(k): int(v) for k, v in frame[col].value_counts(dropna=False).to_dict().items()}
    return {
        "data_mode": data_mode,
        "market_code": market_code,
        "allow_execution_candidates": bool(allow_execution),
        "execution_policy": "LOCKED_UNTIL_WEB_VALIDATION" if not allow_execution else "UNLOCKED_MANUAL_OVERRIDE",
        "raw_count": int(len(raw)) if raw is not None else 0,
        "scored_count": int(len(scored)) if scored is not None else 0,
        "top20_count": int(len(top20)) if top20 is not None else 0,
        "top5_count": int(len(top5)) if top5 is not None else 0,
        "raw_cap_distribution": dist(raw, "cap_bucket"),
        "top20_cap_distribution": dist(top20, "cap_bucket"),
        "top5_cap_distribution": dist(top5, "cap_bucket"),
        "data_quality_distribution": dist(raw, "data_quality_status"),
    }
