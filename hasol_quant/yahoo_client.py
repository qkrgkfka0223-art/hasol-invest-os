from __future__ import annotations

import time
from datetime import date
from typing import Iterable

import pandas as pd
import yfinance as yf


def _empty_bars() -> pd.DataFrame:
    return pd.DataFrame(columns=["ticker", "timestamp", "open", "high", "low", "close", "volume", "trade_count", "vwap"])


def _normalize_download(raw: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    if raw is None or raw.empty:
        return _empty_bars()

    frames: list[pd.DataFrame] = []
    if isinstance(raw.columns, pd.MultiIndex):
        level0 = {str(x).upper() for x in raw.columns.get_level_values(0)}
        field_first = bool(level0 & {"OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"})
        for ticker in tickers:
            try:
                g = raw.xs(ticker, axis=1, level=1 if field_first else 0, drop_level=True).copy()
            except (KeyError, ValueError):
                continue
            g.columns = [str(c).lower().replace(" ", "_") for c in g.columns]
            g["ticker"] = ticker
            frames.append(g.reset_index())
    else:
        g = raw.copy()
        g.columns = [str(c).lower().replace(" ", "_") for c in g.columns]
        g["ticker"] = tickers[0]
        frames.append(g.reset_index())

    if not frames:
        return _empty_bars()

    out = pd.concat(frames, ignore_index=True)
    date_col = next((c for c in out.columns if str(c).lower() in {"date", "datetime", "index"}), None)
    if date_col is None:
        raise ValueError("Yahoo download did not provide a date column")
    out = out.rename(columns={date_col: "timestamp"})
    required = ["open", "high", "low", "close", "volume"]
    for col in required:
        if col not in out.columns:
            out[col] = pd.NA
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    out["ticker"] = out["ticker"].astype(str).str.upper()
    for col in required:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out["trade_count"] = pd.NA
    out["vwap"] = pd.NA
    return out[["ticker", "timestamp", "open", "high", "low", "close", "volume", "trade_count", "vwap"]].dropna(subset=["timestamp", "close"])


def _download(tickers: list[str], *, period: str) -> pd.DataFrame:
    """Use serial yfinance IO to avoid its shared sqlite cache lock races."""
    if not tickers:
        return _empty_bars()
    raw = yf.download(
        tickers=tickers,
        period=period,
        interval="1d",
        auto_adjust=False,
        actions=False,
        group_by="column",
        threads=False,
        progress=False,
        timeout=30,
    )
    return _normalize_download(raw, tickers)


def _download_with_missing_retries(batch: list[str], *, period: str, retries: int = 2) -> pd.DataFrame:
    """Fetch a batch, then retry only missing symbols serially.

    yfinance can report individual failures without raising an exception. Missing
    symbols therefore get bounded single-symbol retries. Permanent no-history
    cases remain missing and are handled honestly by the downstream coverage gate.
    """
    try:
        base = _download(batch, period=period)
    except Exception:
        base = _empty_bars()

    frames = [base] if not base.empty else []
    returned = set(base["ticker"].astype(str)) if not base.empty else set()
    missing = [ticker for ticker in batch if ticker not in returned]

    for attempt in range(retries):
        if not missing:
            break
        next_missing: list[str] = []
        if attempt:
            time.sleep(0.5 * attempt)
        for ticker in missing:
            try:
                one = _download([ticker], period=period)
            except Exception:
                one = _empty_bars()
            if one.empty:
                next_missing.append(ticker)
            else:
                frames.append(one)
        missing = next_missing

    if not frames:
        return _empty_bars()
    return pd.concat(frames, ignore_index=True).drop_duplicates(subset=["ticker", "timestamp"], keep="last")


def fetch_daily_bars(
    tickers: Iterable[str],
    *,
    completed_before_et: date,
    period: str = "6mo",
    batch_size: int = 80,
) -> pd.DataFrame:
    """Fetch detection-only Yahoo daily bars and exclude the prediction date.

    Yahoo/yfinance is NOT a canonical market-fact source in HASOL. It is used only
    for candidate Quant screening. Final candidate market facts are revalidated
    through the connected Alpaca market-data tool.
    """
    symbols = sorted({str(t).upper().strip() for t in tickers if str(t).strip()})
    rows: list[pd.DataFrame] = []
    for start in range(0, len(symbols), batch_size):
        batch = symbols[start : start + batch_size]
        frame = _download_with_missing_retries(batch, period=period)
        if not frame.empty:
            rows.append(frame)
    if not rows:
        return pd.DataFrame()
    out = pd.concat(rows, ignore_index=True)
    # yfinance daily timestamps are session-date labels. Pre-market runs may not
    # use the prediction day's bar even if a provider exposes a partial record.
    out = out[out["timestamp"].dt.date < completed_before_et].copy()
    return out.sort_values(["ticker", "timestamp"]).reset_index(drop=True)
