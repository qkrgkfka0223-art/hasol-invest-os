from __future__ import annotations

from io import StringIO
import re

import pandas as pd
import requests

from .config import NASDAQ_LISTED_URL, OTHER_LISTED_URL

# Deterministic reference-universe purity gate.  This intentionally filters by
# the listed security name instead of assuming ETF=N means common equity.
# Foreign operating-company ordinary/common shares remain allowed, while
# depositary receipts/shares and other non-common security forms are excluded.
EXCLUDE_NAME_RE = re.compile(
    r"\b("
    r"warrant|warrants|right|rights|unit|units|preferred|preference|"
    r"closed[- ]end|exchange[- ]traded|etn|etns|notes due|income fund|"
    r"acquisition corp|acquisition company|blank check|"
    r"american depositary share|american depositary shares|"
    r"american depositary receipt|american depositary receipts|"
    r"american depository share|american depository shares|"
    r"american depository receipt|american depository receipts|"
    r"depositary receipt|depositary receipts|depository receipt|depository receipts|"
    r"depositary share|depositary shares|depository share|depository shares|"
    r"shares of beneficial interest|units of beneficial interest|"
    r"limited partnership unit|limited partnership units"
    r")\b",
    flags=re.IGNORECASE,
)


def is_common_equity_security_name(name: object) -> bool:
    text = str(name or "").strip()
    if not text:
        return False
    return EXCLUDE_NAME_RE.search(text) is None


def _parse_pipe_table(text: str) -> pd.DataFrame:
    lines = [line for line in text.splitlines() if line.strip() and not line.startswith("File Creation Time")]
    # Exchange symbols such as the valid ticker `NA` must never be interpreted as a null token.
    return pd.read_csv(StringIO("\n".join(lines)), sep="|", keep_default_na=False, na_filter=False)


def _download_pipe_table(url: str, timeout: int = 30) -> pd.DataFrame:
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "HASOL/1.0"})
    resp.raise_for_status()
    return _parse_pipe_table(resp.text)


def _clean_nasdaq(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    x = x[x["Test Issue"].astype(str).str.upper().eq("N")]
    x = x[x["ETF"].astype(str).str.upper().eq("N")]
    x = x.rename(columns={"Symbol": "ticker", "Security Name": "security_name"})
    x["listing_source"] = "NASDAQ"
    return x[["ticker", "security_name", "listing_source"]]


def _clean_other(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    x = x[x["Test Issue"].astype(str).str.upper().eq("N")]
    x = x[x["ETF"].astype(str).str.upper().eq("N")]
    x = x.rename(columns={"ACT Symbol": "ticker", "Security Name": "security_name"})
    x["listing_source"] = x.get("Exchange", "OTHER")
    return x[["ticker", "security_name", "listing_source"]]


def load_reference_universe() -> pd.DataFrame:
    nasdaq = _clean_nasdaq(_download_pipe_table(NASDAQ_LISTED_URL))
    other = _clean_other(_download_pipe_table(OTHER_LISTED_URL))
    ref = pd.concat([nasdaq, other], ignore_index=True)
    ref["ticker"] = ref["ticker"].astype(str).str.upper().str.strip()
    ref["security_name"] = ref["security_name"].astype(str).str.strip()
    ref = ref[ref["ticker"].ne("")]
    ref = ref[ref["security_name"].map(is_common_equity_security_name)]
    # ^ and $ are CQS preferred/special issue delimiters; / is not an Alpaca common-stock symbol form.
    # Dot-class common shares (e.g. BRK.B) remain valid and are retained.
    ref = ref[~ref["ticker"].str.contains(r"[\^$/]", regex=True, na=False)]
    return ref.drop_duplicates("ticker").reset_index(drop=True)


def build_tradable_universe(reference_df: pd.DataFrame, assets_df: pd.DataFrame) -> pd.DataFrame:
    a = assets_df.copy()
    a["ticker"] = a["ticker"].astype(str).str.upper()
    a = a[a["tradable"].eq(True)]
    out = reference_df.merge(a, on="ticker", how="inner", suffixes=("_ref", "_alpaca"))
    out = out[~out["exchange"].astype(str).str.upper().isin(["OTC"])]
    return out.sort_values("ticker").drop_duplicates("ticker").reset_index(drop=True)


def apply_market_liquidity_gate(universe_df: pd.DataFrame, features_df: pd.DataFrame, min_price: float = 3.0, min_adv20_usd: float = 10_000_000.0, min_sessions: int = 20) -> pd.DataFrame:
    f = features_df[["ticker", "close", "adv20_usd", "history_bars"]].copy()
    merged = universe_df.merge(f, on="ticker", how="left")
    mask = merged["close"].ge(min_price) & merged["adv20_usd"].ge(min_adv20_usd) & merged["history_bars"].ge(min_sessions)
    return merged.loc[mask, ["ticker"]].drop_duplicates().reset_index(drop=True)
