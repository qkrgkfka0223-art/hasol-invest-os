from __future__ import annotations

from pathlib import Path
from typing import Iterable
import pandas as pd

from .universe import load_universe
from .source_price_movers import load_price_mover_seed_candidates
from .source_news_catalysts import load_news_catalyst_seed_candidates
from .source_earnings import load_earnings_seed_candidates
from .source_biotech_fda import load_biotech_fda_seed_candidates

REQUIRED_COLUMNS = [
    "ticker",
    "company",
    "candidate_source",
    "source_reason",
    "headline",
    "source_confidence",
    "requires_web_validation",
]


def _ensure_columns(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    out = df.copy()
    if "ticker" not in out.columns:
        raise ValueError(f"{source_name} candidate source must contain ticker")
    out["ticker"] = out["ticker"].astype(str).str.upper().str.strip()
    out = out[out["ticker"].ne("")]
    defaults = {
        "company": "",
        "candidate_source": source_name,
        "source_reason": source_name,
        "headline": "",
        "source_confidence": "DISCOVERY_ONLY",
        "requires_web_validation": True,
    }
    for col, default in defaults.items():
        if col not in out.columns:
            out[col] = default
    out["candidate_source"] = out["candidate_source"].fillna(source_name).astype(str)
    out["source_reason"] = out["source_reason"].fillna("").astype(str)
    out["headline"] = out["headline"].fillna(out["source_reason"]).astype(str)
    out["source_confidence"] = out["source_confidence"].fillna("DISCOVERY_ONLY").astype(str)
    out["requires_web_validation"] = out["requires_web_validation"].fillna(True).astype(bool)
    return out[REQUIRED_COLUMNS]


def _seed_universe_frame(path: str | None) -> pd.DataFrame:
    base = load_universe(path)
    base["candidate_source"] = "universe_seed"
    base["company"] = base.get("company", "")
    base["source_reason"] = "existing universe seed candidate"
    base["headline"] = base.get("headline", "existing universe seed candidate")
    base["source_confidence"] = "SEED_UNIVERSE"
    base["requires_web_validation"] = True
    return _ensure_columns(base, "universe_seed")


def _external_candidates_frame(path: str | None) -> pd.DataFrame:
    if not path:
        return pd.DataFrame(columns=REQUIRED_COLUMNS)
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"External candidate CSV not found: {path}")
    df = pd.read_csv(p)
    if "candidate_source" not in df.columns:
        df["candidate_source"] = "external_web_candidates"
    if "source_confidence" not in df.columns:
        df["source_confidence"] = "EXTERNAL_DISCOVERY_ONLY"
    if "requires_web_validation" not in df.columns:
        df["requires_web_validation"] = True
    return _ensure_columns(df, "external_web_candidates")


def _combine_text(values: Iterable[object], sep: str = " | ") -> str:
    seen: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text.lower() != "nan" and text not in seen:
            seen.append(text)
    return sep.join(seen)


def build_candidate_pool(
    universe_csv: str | None = None,
    external_candidates_csv: str | None = None,
    include_seed_sources: bool = True,
) -> pd.DataFrame:
    """Build the broad discovery universe before price/event scoring.

    The output is not a buy list. It is the raw candidate pool that will be
    price-fetched, tagged, filtered, and compressed by later stages.
    """
    frames = [_seed_universe_frame(universe_csv)]
    ext = _external_candidates_frame(external_candidates_csv)
    if not ext.empty:
        frames.append(ext)
    if include_seed_sources:
        frames.extend([
            load_price_mover_seed_candidates(),
            load_news_catalyst_seed_candidates(),
            load_earnings_seed_candidates(),
            load_biotech_fda_seed_candidates(),
        ])

    normalised = [_ensure_columns(f, f"source_{idx}") for idx, f in enumerate(frames) if f is not None and not f.empty]
    if not normalised:
        return pd.DataFrame(columns=REQUIRED_COLUMNS + ["source_count", "candidate_reason", "source_list", "web_validation_required"])

    raw = pd.concat(normalised, ignore_index=True)
    raw = raw.dropna(subset=["ticker"])
    raw["ticker"] = raw["ticker"].astype(str).str.upper().str.strip()
    raw = raw[raw["ticker"].ne("")]

    grouped = raw.groupby("ticker", as_index=False).agg({
        "company": lambda x: _combine_text(x, " / "),
        "candidate_source": lambda x: _combine_text(x, ";"),
        "source_reason": lambda x: _combine_text(x, " | "),
        "headline": lambda x: _combine_text(x, " | "),
        "source_confidence": lambda x: _combine_text(x, ";"),
        "requires_web_validation": "max",
    })
    grouped["source_count"] = raw.groupby("ticker")["candidate_source"].nunique().reindex(grouped["ticker"]).values
    grouped["source_list"] = grouped["candidate_source"]
    grouped["candidate_reason"] = grouped["source_reason"]
    grouped["web_validation_required"] = grouped["requires_web_validation"].astype(bool)
    grouped["discovery_status"] = "RAW_DISCOVERY_NOT_VALIDATED"
    return grouped.sort_values(["source_count", "ticker"], ascending=[False, True]).reset_index(drop=True)


def attach_candidate_context(profile_df: pd.DataFrame, candidate_pool: pd.DataFrame) -> pd.DataFrame:
    """Merge raw discovery context onto fetched price profiles."""
    if candidate_pool is None or candidate_pool.empty:
        return profile_df
    context_cols = [
        "ticker", "candidate_source", "source_count", "source_list", "candidate_reason",
        "source_confidence", "web_validation_required", "discovery_status",
    ]
    context = candidate_pool[[c for c in context_cols if c in candidate_pool.columns]].copy()
    out = profile_df.merge(context, on="ticker", how="left")
    out["candidate_source"] = out.get("candidate_source", "").fillna("price_fetch_only")
    out["source_count"] = pd.to_numeric(out.get("source_count", 1), errors="coerce").fillna(1).astype(int)
    out["candidate_reason"] = out.get("candidate_reason", "").fillna("")
    out["source_confidence"] = out.get("source_confidence", "").fillna("PRICE_ONLY")
    out["web_validation_required"] = out.get("web_validation_required", True).fillna(True).astype(bool)
    original_headline = out.get("headline", "").fillna("").astype(str)
    candidate_reason = out["candidate_reason"].fillna("").astype(str)
    out["headline"] = (original_headline + " | " + candidate_reason).str.strip(" |")
    return out
