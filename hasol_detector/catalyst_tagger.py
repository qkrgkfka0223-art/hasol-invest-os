from __future__ import annotations
import pandas as pd
from .config import AXIS_KEYWORDS, FAMOUS_PARTNER_KEYWORDS, BIOTECH_EXPANSION_KEYWORDS, BAD_EVENT_KEYWORDS

EVENT_KEYWORDS = {
    "EARNINGS": ["earnings", "guidance", "revenue", "profit", "EPS", "margin", "backlog"],
    "GUIDANCE_RAISE": ["guidance raise", "raised guidance", "raises outlook", "outlook raised"],
    "BACKLOG_INCREASE": ["backlog", "record backlog", "bookings", "order growth"],
    "FDA": ["FDA", "clinical", "trial", "Phase", "approval", "clearance", "NDA", "PDUFA"],
    "CLINICAL_SUCCESS": ["late-stage trial", "met primary endpoint", "primary endpoint met", "Phase 3", "reduced symptoms", "statistically significant"],
    "BLA_ACCEPTED": ["BLA accepted", "resubmitted BLA", "BLA resubmission", "accepted BLA"],
    "BIOTECH_LICENSE": ["exclusive rights", "licensing deal", "license agreement", "pipeline expansion"],
    "M&A": ["acquire", "merger", "takeover", "buyout", "strategic alternatives"],
    "IPO": ["IPO", "S-1", "newly public"],
    "POLICY": ["policy", "tariff", "subsidy", "regulation", "government"],
    "DEFENSE": ["defense", "drone", "military", "DoD", "Army", "Navy", "public safety"],
    "SPACE": ["space", "lunar", "satellite", "launch", "NASA", "SpaceX", "Artemis", "Starlink"],
    "PRODUCT": ["launch", "product", "platform", "upgrade", "certification"],
    "CAPEX": ["capex", "capacity", "factory", "facility", "expansion"],
    "SUPPLY_SHORTAGE": ["shortage", "supply", "constraint", "supply-chain", "supply chain"],
    "INSIDER_BUY": ["Form 4", "insider buy", "insider purchase", "open market purchase"],
    "SEC_CLUSTER": ["Form 3", "Form 4", "13D", "13G", "8-K cluster", "ownership cluster"],
    "OWNERSHIP_CHANGE": ["13D", "13G", "ownership", "stake", "large holder", "activist"],
    "COMPLIANCE_RECOVERY": ["Nasdaq compliance", "compliance regained", "listing compliance"],
    "GOV_CONTRACT": ["contract", "award", "government", "federal"],
    "AI_INFRA": ["AI", "compute", "GPU", "data center", "AMD", "NVIDIA", "server", "optical", "cloud"],
    "DATA_CENTER": ["data center", "30MW", "power", "compute", "cooling", "hosting"],
    "FAMOUS_PARTNER": FAMOUS_PARTNER_KEYWORDS,
    "SHORT_SQUEEZE": ["short interest", "squeeze"],
}

def _contains_term(text: str, term: str) -> bool:
    import re
    t = (text or "").lower()
    term_l = term.lower()
    if " " in term_l or any(ch.isdigit() for ch in term_l) or "-" in term_l:
        return term_l in t
    return re.search(r"\b" + re.escape(term_l) + r"\b", t) is not None

def _match_tags(text: str, mapping: dict[str, list[str]]) -> list[str]:
    tags = []
    for tag, words in mapping.items():
        if any(_contains_term(text, w) for w in words):
            tags.append(tag)
    return tags

def _sec_cluster_tag(sec_forms: str, sec_note: str) -> bool:
    text = f"{sec_forms or ''} {sec_note or ''}"
    forms = []
    for f in ["Form 3", "Form 4", "13D", "13G", "8-K", "6-K"]:
        if _contains_term(text, f):
            forms.append(f)
    return len(set(forms)) >= 2

def _biotech_expansion_tag(text: str) -> bool:
    return any(_contains_term(text, k) for k in BIOTECH_EXPANSION_KEYWORDS)

def _bad_event_tags(text: str) -> list[str]:
    return [k for k in BAD_EVENT_KEYWORDS if _contains_term(text, k)]

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

    combined = (
        out.get("headline", "").fillna("") + " " +
        out.get("candidate_reason", "").fillna("") + " " +
        out.get("candidate_source", "").fillna("") + " " +
        out.get("sec_event", "").fillna("") + " " +
        out.get("sec_form", "").fillna("") + " " +
        out.get("sec_note", "").fillna("")
    )

    event_tags = []
    axis_tags = []
    famous_partner_hits = []
    biotech_hits = []
    sec_cluster_flags = []
    bad_event_hits = []
    for idx, text in combined.items():
        tags = _match_tags(text, EVENT_KEYWORDS)
        sec_cluster = _sec_cluster_tag(out.loc[idx].get("sec_form", ""), out.loc[idx].get("sec_note", ""))
        if sec_cluster and "SEC_CLUSTER" not in tags:
            tags.append("SEC_CLUSTER")
        if _biotech_expansion_tag(text):
            if "BIOTECH_LICENSE" not in tags and "CLINICAL_SUCCESS" not in tags and "BLA_ACCEPTED" not in tags:
                tags.append("BIOTECH_LICENSE")
        ax = _match_tags(text, AXIS_KEYWORDS)
        partners = [k for k in FAMOUS_PARTNER_KEYWORDS if _contains_term(text, k)]
        bios = [k for k in BIOTECH_EXPANSION_KEYWORDS if _contains_term(text, k)]
        bads = _bad_event_tags(text)
        event_tags.append(";".join(tags) or "NONE")
        axis_tags.append(";".join(ax) or "NONE")
        famous_partner_hits.append(";".join(partners))
        biotech_hits.append(";".join(bios))
        sec_cluster_flags.append(bool(sec_cluster))
        bad_event_hits.append(";".join(bads))

    out["event_tags"] = event_tags
    out["axis_tags"] = axis_tags
    out["famous_partner_hits"] = famous_partner_hits
    out["biotech_event_hits"] = biotech_hits
    out["sec_cluster_flag"] = sec_cluster_flags
    out["bad_event_hits"] = bad_event_hits
    out["bad_event_flag"] = out["bad_event_hits"].astype(str).str.len() > 0
    out["primary_event"] = out["event_tags"].apply(lambda s: s.split(";")[0] if s else "NONE")
    out["primary_axis"] = out["axis_tags"].apply(lambda s: s.split(";")[0] if s else "NONE")
    return out
