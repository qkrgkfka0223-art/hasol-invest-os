from __future__ import annotations
import pandas as pd
from typing import Iterable

SAMPLE_SEC_EVENTS = {
    "CRVO": [{"form":"Form 4", "event":"INSIDER_BUY", "quality":"B", "note":"large holder / insider transaction cluster"}],
    "RXT": [{"form":"8-K", "event":"AI_INFRA", "quality":"A", "note":"AMD AI compute deployment agreement"}],
    "CUPR": [{"form":"8-K", "event":"FDA", "quality":"C", "note":"FDA-related move already reversing"}],
    "CAI": [{"form":"S-1", "event":"IPO", "quality":"B", "note":"IPO/diagnostics watch"}],
}

def scan_sample_sec_events(tickers: Iterable[str]) -> pd.DataFrame:
    rows = []
    for t in tickers:
        for ev in SAMPLE_SEC_EVENTS.get(str(t).upper(), []):
            rows.append({"ticker": str(t).upper(), **ev})
    return pd.DataFrame(rows, columns=["ticker", "form", "event", "quality", "note"])

def scan_sec_events(tickers: Iterable[str], sample: bool = True) -> pd.DataFrame:
    if sample:
        return scan_sample_sec_events(tickers)
    try:
        from edgar import set_identity, Company
    except Exception as exc:
        raise RuntimeError("edgartools is not installed. Run `pip install edgartools` or use --sample.") from exc
    rows = []
    for ticker in tickers:
        rows.append({"ticker": str(ticker).upper(), "form": None, "event": None, "quality": None, "note": "live SEC scanner hook not expanded"})
    return pd.DataFrame(rows)
