from __future__ import annotations

from io import StringIO
import pandas as pd

NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"


def _read_pipe_file(url: str) -> pd.DataFrame:
    df = pd.read_csv(url, sep="|", dtype=str)
    df = df.dropna(how="all")
    if "File Creation Time" in str(df.tail(1).to_dict()):
        df = df.iloc[:-1]
    return df


def load_us_listed_universe(include_etfs: bool = False, limit: int | None = None) -> pd.DataFrame:
    """Load US listed tickers from Nasdaq Trader symbol directories.

    This is for mover generation, not execution approval.
    It intentionally keeps a broad universe before execution filters.
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
    df = df.drop_duplicates("ticker").sort_values("ticker").reset_index(drop=True)
    if limit:
        df = df.head(limit)
    return df
