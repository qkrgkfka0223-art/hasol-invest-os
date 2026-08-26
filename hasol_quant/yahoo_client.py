from __future__ import annotations

from datetime import date
from typing import Iterable

import pandas as pd
import yfinance as yf


def _normalize_download(raw: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    if raw is None or raw.empty:
        return pd.DataFrame(columns=["ticker", "timestamp", "open", "high", "low", "close", "volume", "trade_count", "vwap"])

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
        return pd.DataFrame(columns=["ticker", "timestamp", "open", "high", "low", "close", "volume", "trade_count", "vwap"])

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
        raw = yf.download(
            tickers=batch,
            period=period,
            interval="1d",
            auto_adjust=False,
            actions=False,
            group_by="column",
            threads=True,
            progress=False,
            timeout=30,
        )
        rows.append(_normalize_download(raw, batch))
    if not rows:
        return pd.DataFrame()
    out = pd.concat(rows, ignore_index=True)
    # yfinance daily timestamps are session-date labels. Pre-market runs may not
    # use the prediction day's bar even if a provider exposes a partial record.
    out = out[out["timestamp"].dt.date < completed_before_et].copy()
    return out.sort_values(["ticker", "timestamp"]).reset_index(drop=True)
