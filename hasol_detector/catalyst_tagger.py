from __future__ import annotations
import pandas as pd
from .config import AXIS_KEYWORDS

EVENT_KEYWORDS = {
    "EARNINGS": ["earnings", "guidance", "revenue", "profit", "EPS"],
    "FDA": ["FDA", "clinical", "trial", "Phase", "approval", "clearance"],
    "M&A": ["acquire", "merger", "takeover", "buyout"],
    "IPO": ["IPO", "S-1", "newly public"],
    "POLICY": ["policy", "tariff", "subsidy", "regulation", "government"],
    "DEFENSE": ["defense", "drone", "military", "DoD", "Army", "Navy"],
    "SPACE": ["space", "lunar", "satellite", "launch", "NASA"],
    "PRODUCT": ["launch", "product", "platform", "upgrade"],
    "CAPEX": ["capex", "capacity", "factory", "facility", "expansion"],
    "SUPPLY_SHORTAGE": ["shortage", "supply", "constraint"],
    "INSIDER_BUY": ["Form 4", "insider", "13D", "large holder"],
    "GOV_CONTRACT": ["contract", "award", "government", "federal"],
    "AI_INFRA": ["AI", "compute", "GPU", "data center", "AMD", "NVIDIA"],
    "DATA_CENTER": ["data center", "30MW", "power", "compute"],
    "SHORT_SQUEEZE": ["short interest", "squeeze"],
}

def _contains_term(text: str, term: str) -> bool:
    import re
    t = (text or "").lower()
    term_l = term.lower()
    if " " in term_l or any(ch.isdigit() for ch in term_l):
        return term_l in t
    return re.search(r"\b" + re.escape(term_l) + r"\b", t) is not None

def _match_tags(text: str, mapping: dict[str, list[str]]) -> list[str]:
    tags = []
    for tag, words in mapping.items():
        if any(_contains_term(text, w) for w in words):
            tags.append(tag)
    return tags

def tag_catalysts(df: pd.DataFrame, sec_events: pd.DataFrame | None = None) -> pd.DataFrame:
    out = df.copy()
    if sec_events is not None and not sec_events.empty:
        sec_agg = sec_events.groupby("ticker").agg({
            "event": lambda x: ";".join(sorted(set([str(v) for v in x if pd.notna(v)]))),
            "form": lambda x: ";".join(sorted(set([str(v) for v in x if pd.notna(v)]))),
            "note": lambda x: " | ".join([str(v) for v in x if pd.notna(v)]),
        }).reset_index().rename(columns={"event":"sec_event", "form":"sec_form", "note":"sec_note"})
        out = out.merge(sec_agg, on="ticker", how="left")
    else:
        out["sec_event"] = ""
        out["sec_form"] = ""
        out["sec_note"] = ""

    combined = (out.get("headline", "").fillna("") + " " + out.get("sec_event", "").fillna("") + " " + out.get("sec_form", "").fillna("") + " " + out.get("sec_note", "").fillna(""))
    out["event_tags"] = combined.apply(lambda x: ";".join(_match_tags(x, EVENT_KEYWORDS)) or "NONE")
    out["axis_tags"] = combined.apply(lambda x: ";".join(_match_tags(x, AXIS_KEYWORDS)) or "NONE")
    out["primary_event"] = out["event_tags"].apply(lambda s: s.split(";")[0] if s else "NONE")
    out["primary_axis"] = out["axis_tags"].apply(lambda s: s.split(";")[0] if s else "NONE")
    return out
