from __future__ import annotations
import pandas as pd


def add_post_spike_stage(df: pd.DataFrame) -> pd.DataFrame:
    """Classify whether a move is day1, continuation, parabolic, or fading.

    This is not a buy/sell signal. It exists to separate detection from chase risk.
    """
    out = df.copy()
    stages = []
    for _, r in out.iterrows():
        change = float(r.get("change_pct", 0) or 0)
        ret3 = float(r.get("return_3d", 0) or 0)
        ret5 = float(r.get("return_5d", 0) or 0)
        relvol = float(r.get("relative_volume", 0) or 0)
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
        stages.append(stage)
    out["post_spike_stage"] = stages
    out["is_chase_risk"] = out["post_spike_stage"].isin(["day2_continuation", "day3_parabolic", "post_climax_fade", "watch_for_fade"])
    return out
