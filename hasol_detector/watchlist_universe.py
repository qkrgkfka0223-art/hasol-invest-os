from __future__ import annotations

from pathlib import Path
import pandas as pd

WATCHLIST_COLUMNS = [
    "ticker",
    "watchlist_group",
    "watchlist_axis",
    "watchlist_event_type",
    "watch_reason",
    "liquidity_bucket",
    "risk_bucket",
    "execution_allowed",
]


def default_watchlist_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "candidate_universe.csv"


def load_watchlist_universe(path: str | None = None) -> pd.DataFrame:
    p = Path(path) if path else default_watchlist_path()
    if not p.exists():
        return pd.DataFrame(columns=WATCHLIST_COLUMNS)
    df = pd.read_csv(p)
    rename = {
        "group": "watchlist_group",
        "axis": "watchlist_axis",
        "event_type": "watchlist_event_type",
    }
    df = df.rename(columns=rename)
    for col in WATCHLIST_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    df = df[df["ticker"].ne("")]
    df["watchlist_group"] = df["watchlist_group"].fillna("").astype(str).str.upper().str.strip()
    df["execution_allowed"] = df["execution_allowed"].fillna("no").astype(str).str.lower().str.strip()
    return df[WATCHLIST_COLUMNS].drop_duplicates("ticker").reset_index(drop=True)


def watchlist_as_candidates(path: str | None = None) -> pd.DataFrame:
    df = load_watchlist_universe(path)
    if df.empty:
        return pd.DataFrame(columns=["ticker", "company", "candidate_source", "source_reason", "headline", "source_confidence", "requires_web_validation"] + WATCHLIST_COLUMNS[1:])
    out = df.copy()
    out["company"] = ""
    out["candidate_source"] = "watchlist_universe"
    out["source_reason"] = out["watchlist_group"] + ":" + out["watchlist_axis"] + " | " + out["watch_reason"]
    out["headline"] = out["source_reason"]
    out["source_confidence"] = "WATCHLIST_PRIOR"
    out["requires_web_validation"] = True
    cols = ["ticker", "company", "candidate_source", "source_reason", "headline", "source_confidence", "requires_web_validation"] + WATCHLIST_COLUMNS[1:]
    return out[cols]
