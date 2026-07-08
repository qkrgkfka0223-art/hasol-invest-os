from __future__ import annotations
import pandas as pd
from .config import HasolConfig


def _safe_float(value, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def add_post_spike_stage(df: pd.DataFrame, config: HasolConfig | None = None) -> pd.DataFrame:
    """Separate code detection phase from HASOL judgment.

    Code classifies the phase. HASOL decides whether the phase has an executable thesis.
    """
    config = config or HasolConfig()
    out = df.copy()
    stages, phases, reasons, phase_ok = [], [], [], []

    for _, r in out.iterrows():
        change = _safe_float(r.get("change_pct"))
        ret3 = _safe_float(r.get("return_3d"))
        ret5 = _safe_float(r.get("return_5d"))
        relvol = _safe_float(r.get("relative_volume"))
        gap = _safe_float(r.get("gap_pct"))
        parabolic = bool(r.get("parabolic_3d_flag", False))
        climax = bool(r.get("climax_volume_flag", False))
        wick = bool(r.get("long_upper_wick_flag", False))

        if change >= 70 or parabolic or (ret3 >= 100 and relvol >= 5):
            stage = "day3_parabolic"
        elif change >= 25 and ret3 >= 45:
            stage = "day2_continuation"
        elif change >= 15 and relvol >= 2 and ret5 < 60:
            stage = "day1_spike"
        elif change < -10 and (ret3 > 40 or ret5 > 60):
            stage = "post_climax_fade"
        elif climax or wick:
            stage = "watch_for_fade"
        else:
            stage = "base_or_quiet_rs"

        if change >= config.climax_change or parabolic or (ret3 >= 100 and relvol >= 5):
            phase, reason = "CLIMAX_REVIEW_ONLY", "already extended: climax/parabolic risk"
        elif config.early_signal_max_change <= change < config.hot_signal_max_change:
            phase, reason = "HOT_SIGNAL_WATCH_ONLY", "hot move; web validation and pullback needed"
        elif (config.early_signal_min_change <= change < config.early_signal_max_change and relvol >= config.early_relvol_min and not parabolic and not climax and not wick and ret5 < 60):
            phase, reason = "EARLY_SIGNAL", "early price/volume expansion before confirmed climax"
        elif change < -10 and (ret3 > 40 or ret5 > 60):
            phase, reason = "POST_CLIMAX_FADE", "prior spike is fading"
        elif relvol >= config.early_relvol_min and change < config.early_signal_min_change:
            phase, reason = "QUIET_RS_VOLUME_EXPANSION", "volume expands before price expansion"
        elif gap >= config.early_signal_min_change and change < config.early_signal_max_change:
            phase, reason = "GAP_EARLY_SIGNAL", "gap is early but must hold VWAP/previous high"
        else:
            phase, reason = "BASE_OR_QUIET_RS", "no confirmed early breakout; keep as watch candidate"

        ok = phase in {"EARLY_SIGNAL", "GAP_EARLY_SIGNAL", "QUIET_RS_VOLUME_EXPANSION", "BASE_OR_QUIET_RS"}
        if stage in {"day2_continuation", "day3_parabolic", "post_climax_fade", "watch_for_fade"}:
            ok = False

        stages.append(stage)
        phases.append(phase)
        reasons.append(reason)
        phase_ok.append(ok)

    out["post_spike_stage"] = stages
    out["move_phase"] = phases
    out["move_phase_reason"] = reasons
    out["execution_phase_ok"] = phase_ok
    out["is_chase_risk"] = (
        out["post_spike_stage"].isin(["day2_continuation", "day3_parabolic", "post_climax_fade", "watch_for_fade"])
        | out["move_phase"].isin(["HOT_SIGNAL_WATCH_ONLY", "CLIMAX_REVIEW_ONLY", "POST_CLIMAX_FADE"])
    )
    return out
