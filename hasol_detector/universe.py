from __future__ import annotations
import pandas as pd
from pathlib import Path

SAMPLE_TICKERS = [
    "RXT", "BEEM", "CRVO", "IVDA", "SUGP", "SLBT", "GDHG", "TDIC", "IMCC", "RGNT",
    "CAST", "CUPR", "PRFX", "INMD", "UAA", "ATHM", "PRTA", "CAI", "NPB", "IESC",
    "LOAR", "MIRM", "NVDA", "AMD", "PLTR", "SMCI", "RKLB", "LUNR", "ASTS", "SOUN",
]

def build_sample_universe() -> pd.DataFrame:
    return pd.DataFrame({"ticker": SAMPLE_TICKERS})

def load_universe(path: str | None = None) -> pd.DataFrame:
    if path:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Universe file not found: {path}")
        df = pd.read_csv(p)
        if "ticker" not in df.columns:
            raise ValueError("Universe CSV must contain a 'ticker' column")
        df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
        return df.drop_duplicates("ticker")
    return build_sample_universe()
