from __future__ import annotations

import re
import pandas as pd

NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"

NON_COMMON_SECURITY_PATTERN = re.compile(
    r"\b(warrant|warrants|unit|units|right|rights|preferred|preference|depositary|"
    r"note|notes|bond|bonds|debenture|fund|etf|etn|beneficial interest|acquisition corp)\b",
    re.IGNORECASE,
)


def _read_pipe_file(url: str) -> pd.DataFrame:
    df = pd.read_csv(url, sep="|", dtype=str)
    df = df.dropna(how="all")
    if "File Creation Time" in str(df.tail(1).to_dict()):
        df = df.iloc[:-1]
    return df


def _tradable_common_stock_filter(df: pd.DataFrame) -> pd.DataFrame:
    """Remove obvious non-operating securities from the discovery universe.

    The detector may still ingest a special security through an explicit event source,
    but the broad market universe should be common/ordinary operating-company shares.
    """
    out = df.copy()
    ticker = out["ticker"].astype(str).str.upper().str.strip()
    company = out["company"].astype(str).str.strip()

    # Nasdaq/NYSE symbol directories include warrants, rights, units and preferreds.
    # Most use punctuation or W/U/R/P suffix conventions; company names provide a
    # second guard for exceptions.
    simple_symbol = ticker.str.match(r"^[A-Z]{1,5}$", na=False)
    suffix_security = ticker.str.endswith(("W", "U", "R"), na=False) & ticker.str.len().ge(4)
    non_common_name = company.str.contains(NON_COMMON_SECURITY_PATTERN, na=False)

    out = out[simple_symbol & ~suffix_security & ~non_common_name]
    return out


def load_us_listed_universe(
    include_etfs: bool = False,
    limit: int | None = None,
    sample: bool = False,
    seed: int = 42,
    common_only: bool = True,
) -> pd.DataFrame:
    """Load US-listed tickers from Nasdaq Trader symbol directories.

    Use sample=True for a deterministic cross-market sample rather than an
    alphabetically biased slice. Use limit=None for the full universe.
    """
    frames = []
    try:
        nasdaq = _read_pipe_file(NASDAQ_LISTED_URL)
        nasdaq = nasdaq.rename(columns={"Symbol": "ticker", "Security Name": "company", "ETF": "etf", "Test Issue": "test_issue"})
        nasdaq["exchange"] = "NASDAQ"
        frames.append(nasdaq[["ticker", "company", "exchange", "etf", "test_issue"]])
    except Exception:
        pass
    try:
        other = _read_pipe_file(OTHER_LISTED_URL)
        other = other.rename(columns={"ACT Symbol": "ticker", "Security Name": "company", "Exchange": "exchange", "ETF": "etf", "Test Issue": "test_issue"})
        frames.append(other[["ticker", "company", "exchange", "etf", "test_issue"]])
    except Exception:
        pass
    if not frames:
        raise RuntimeError("Could not load US listed universe from Nasdaq Trader symbol directories")

    df = pd.concat(frames, ignore_index=True)
    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    df["company"] = df["company"].astype(str).str.strip()
    df["etf"] = df.get("etf", "N").astype(str).str.upper().str.strip()
    df["test_issue"] = df.get("test_issue", "N").astype(str).str.upper().str.strip()
    df = df[df["ticker"].ne("")]
    df = df[df["test_issue"].ne("Y")]
    if not include_etfs:
        df = df[df["etf"].ne("Y")]
    if common_only:
        df = _tradable_common_stock_filter(df)

    df = df.drop_duplicates("ticker").sort_values("ticker").reset_index(drop=True)
    if limit:
        if sample:
            df = df.sample(n=min(limit, len(df)), random_state=seed).sort_values("ticker").reset_index(drop=True)
        else:
            df = df.head(limit)
    return df
