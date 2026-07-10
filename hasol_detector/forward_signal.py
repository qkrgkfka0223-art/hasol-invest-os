from __future__ import annotations
import pandas as pd

FUTURE_EVENT_KEYWORDS = {
    "EARNINGS_UPCOMING": ["earnings date", "reports earnings", "earnings scheduled", "quarterly results", "pre-announced"],
    "FDA_UPCOMING": ["PDUFA", "advisory committee", "FDA decision", "NDA review", "BLA review", "clinical readout", "topline data expected"],
    "INVESTOR_DAY": ["investor day", "analyst day", "capital markets day"],
    "PRODUCT_LAUNCH": ["launches", "product launch", "commercial launch", "rollout"],
    "POLICY_CATALYST": ["tariff", "subsidy", "policy", "bill", "approval expected", "government funding"],
}

FRESH_CATALYST_KEYWORDS = {
    "MATERIAL_AGREEMENT": ["definitive agreement", "material agreement", "strategic agreement", "multi-year contract", "supply agreement"],
    "INSIDER_BUY": ["Form 4", "insider purchase", "open market purchase", "code P"],
    "OWNERSHIP_CHANGE": ["13D", "13G", "activist", "beneficial ownership", "stake increased"],
    "GUIDANCE_RAISE": ["guidance raise", "raises outlook", "raises forecast", "increases guidance"],
    "FDA_SUCCESS": ["FDA approval", "FDA clearance", "NDA accepted", "BLA accepted", "primary endpoint met", "statistically significant"],
    "MAJOR_PARTNER": ["NVIDIA", "AMD", "Microsoft", "Amazon", "Google", "SpaceX", "Starlink", "NASA", "DoD"],
}

RISK_KEYWORDS = [
    "offering", "registered direct", "ATM offering", "warrant", "resale", "S-1", "S-3", "424B",
    "reverse split", "delisting", "going concern", "bankruptcy", "halt", "investigation"
]


def _hits(text: str, mapping: dict[str, list[str]]) -> list[str]:
    low = str(text or "").lower()
    found: list[str] = []
    for tag, words in mapping.items():
        for word in words:
            if word.lower() in low:
                found.append(tag)
                break
    return found


def add_forward_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Add forward-looking signal labels.

    This module does not decide what to buy. It identifies why a ticker deserves web validation before price expansion.
    """
    out = df.copy()
    headlines = out.get("headline", pd.Series([""] * len(out))).fillna("").astype(str)
    changes = pd.to_numeric(out.get("change_pct", 0), errors="coerce").fillna(0)
    relvol = pd.to_numeric(out.get("relative_volume", 0), errors="coerce").fillna(0)
    above_ma20 = out.get("above_ma20", False).fillna(False).astype(bool)
    above_ma50 = out.get("above_ma50", False).fillna(False).astype(bool)
    spy_rel = pd.to_numeric(out.get("spy_relative_5d", 0), errors="coerce").fillna(0)
    qqq_rel = pd.to_numeric(out.get("qqq_relative_5d", 0), errors="coerce").fillna(0)

    future_tags, fresh_tags, risk_tags, forward_scores, forward_reasons = [], [], [], [], []

    for idx, headline in headlines.items():
        f_tags = _hits(headline, FUTURE_EVENT_KEYWORDS)
        c_tags = _hits(headline, FRESH_CATALYST_KEYWORDS)
        r_tags = [w for w in RISK_KEYWORDS if w.lower() in str(headline).lower()]

        change = float(changes.loc[idx])
        rv = float(relvol.loc[idx])
        quiet_rs = bool(above_ma20.loc[idx] and above_ma50.loc[idx] and spy_rel.loc[idx] > 0 and qqq_rel.loc[idx] > 0 and change < 12)
        underreaction = bool(c_tags and -3 <= change <= 20)
        early_volume = bool(rv >= 1.5 and change < 20)

        score = 0
        reasons = []
        if f_tags:
            score += 12
            reasons.append("future_event")
        if c_tags:
            score += 16
            reasons.append("fresh_catalyst")
        if underreaction:
            score += 12
            reasons.append("underreaction")
        if quiet_rs:
            score += 10
            reasons.append("quiet_rs")
        if early_volume:
            score += 6
            reasons.append("early_volume")
        if change > 35:
            score -= 10
            reasons.append("extended_price")
        if change > 80:
            score -= 25
            reasons.append("climax_not_forward")
        if r_tags:
            score -= 30
            reasons.append("risk_keyword")

        future_tags.append(";".join(f_tags))
        fresh_tags.append(";".join(c_tags))
        risk_tags.append(";".join(r_tags))
        forward_scores.append(score)
        forward_reasons.append(";".join(reasons))

    out["future_event_tags"] = future_tags
    out["fresh_catalyst_tags"] = fresh_tags
    out["forward_risk_tags"] = risk_tags
    out["forward_score"] = forward_scores
    out["forward_reason"] = forward_reasons
    out["forward_candidate"] = out["forward_score"] > 0
    return out
