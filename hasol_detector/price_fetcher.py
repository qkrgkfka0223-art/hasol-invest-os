from __future__ import annotations
from typing import Iterable
from datetime import datetime
import random
import pandas as pd

SAMPLE_PROFILES = {
    "RXT": {"company":"Rackspace Technology", "price":7.12, "prev_close":5.47, "market_cap":1_470_000_000, "sector":"Technology", "industry":"IT Services", "headline":"AMD and Rackspace sign definitive agreement for phased 30MW AI compute deployment"},
    "BEEM": {"company":"Beam Global", "price":3.90, "prev_close":3.29, "market_cap":60_000_000, "sector":"Industrials", "industry":"Electrical Equipment", "headline":"Beam Global granted European patent for smart battery"},
    "CRVO": {"company":"CervoMed", "price":9.70, "prev_close":7.75, "market_cap":95_000_000, "sector":"Healthcare", "industry":"Biotechnology", "headline":"Form 4 and 13D cluster indicates large holder buying"},
    "IVDA": {"company":"Iveda Solutions", "price":2.15, "prev_close":1.44, "market_cap":36_000_000, "sector":"Technology", "industry":"Security Software", "headline":"AI video analytics and 10cm real-time location upgrade"},
    "SUGP": {"company":"SU Group", "price":4.50, "prev_close":2.70, "market_cap":75_000_000, "sector":"Industrials", "industry":"Security Services", "headline":"Germany GEZE distribution agreement"},
    "SLBT": {"company":"Selectis Health", "price":5.30, "prev_close":1.02, "market_cap":28_000_000, "sector":"Healthcare", "industry":"Services", "headline":"Extreme premarket momentum"},
    "GDHG": {"company":"Golden Heaven", "price":2.80, "prev_close":1.18, "market_cap":44_000_000, "sector":"Consumer Cyclical", "industry":"Leisure", "headline":"Low-float momentum"},
    "TDIC": {"company":"Dreamland", "price":3.15, "prev_close":1.80, "market_cap":42_000_000, "sector":"Consumer", "industry":"Entertainment", "headline":"Thin liquidity momentum"},
    "IMCC": {"company":"IM Cannabis", "price":2.85, "prev_close":1.91, "market_cap":16_000_000, "sector":"Healthcare", "industry":"Cannabis", "headline":"Cannabis microcap momentum"},
    "RGNT": {"company":"Regenet", "price":1.90, "prev_close":3.10, "market_cap":21_000_000, "sector":"Healthcare", "industry":"Biotechnology", "headline":"Previous-day climax fading"},
    "CAST": {"company":"Casting Group", "price":2.40, "prev_close":2.90, "market_cap":33_000_000, "sector":"Technology", "industry":"Media", "headline":"Previous spike weakening"},
    "CUPR": {"company":"Cuprina", "price":3.20, "prev_close":3.80, "market_cap":58_000_000, "sector":"Healthcare", "industry":"Medical Devices", "headline":"FDA-related move now fading"},
    "PRFX": {"company":"PainReform", "price":2.05, "prev_close":2.98, "market_cap":24_000_000, "sector":"Healthcare", "industry":"Biotechnology", "headline":"Climax reversal after previous surge"},
    "INMD": {"company":"InMode", "price":14.81, "prev_close":14.20, "market_cap":1_150_000_000, "sector":"Healthcare", "industry":"Medical Devices", "headline":"Quiet relative strength after device sector stabilization"},
    "UAA": {"company":"Under Armour", "price":6.08, "prev_close":5.91, "market_cap":2_600_000_000, "sector":"Consumer Cyclical", "industry":"Apparel", "headline":"Turnaround retail relative strength"},
    "ATHM": {"company":"Autohome", "price":18.78, "prev_close":18.01, "market_cap":2_300_000_000, "sector":"Communication Services", "industry":"Internet Content", "headline":"China ADR stabilization"},
    "PRTA": {"company":"Prothena", "price":9.27, "prev_close":8.95, "market_cap":500_000_000, "sector":"Healthcare", "industry":"Biotechnology", "headline":"Biotech base with institutional accumulation"},
    "CAI": {"company":"Caris Life Sciences", "price":18.70, "prev_close":17.80, "market_cap":1_900_000_000, "sector":"Healthcare", "industry":"Diagnostics", "headline":"Diagnostics IPO earnings watch"},
    "NPB": {"company":"Northpointe Bancshares", "price":18.61, "prev_close":18.42, "market_cap":780_000_000, "sector":"Financial", "industry":"Banks", "headline":"Regional bank quiet RS"},
    "IESC": {"company":"IES Holdings", "price":766.54, "prev_close":748.00, "market_cap":15_000_000_000, "sector":"Industrials", "industry":"Engineering", "headline":"Electrical infrastructure earnings momentum"},
    "LOAR": {"company":"Loar Holdings", "price":77.37, "prev_close":75.10, "market_cap":6_800_000_000, "sector":"Industrials", "industry":"Aerospace", "headline":"Aerospace defense component relative strength"},
    "MIRM": {"company":"Mirum Pharmaceuticals", "price":117.28, "prev_close":113.00, "market_cap":5_900_000_000, "sector":"Healthcare", "industry":"Biotechnology", "headline":"Biotech commercial execution strength"},
    "NVDA": {"company":"NVIDIA", "price":155.00, "prev_close":153.00, "market_cap":3_800_000_000_000, "sector":"Technology", "industry":"Semiconductors", "headline":"AI leader but widely known mega cap"},
    "AMD": {"company":"Advanced Micro Devices", "price":178.00, "prev_close":172.50, "market_cap":290_000_000_000, "sector":"Technology", "industry":"Semiconductors", "headline":"AI compute partner and semiconductor momentum"},
    "PLTR": {"company":"Palantir", "price":132.00, "prev_close":128.40, "market_cap":305_000_000_000, "sector":"Technology", "industry":"Software", "headline":"AI software momentum widely known"},
    "SMCI": {"company":"Super Micro Computer", "price":55.00, "prev_close":53.20, "market_cap":32_000_000_000, "sector":"Technology", "industry":"Computer Hardware", "headline":"AI server infrastructure watch"},
    "RKLB": {"company":"Rocket Lab", "price":23.50, "prev_close":22.10, "market_cap":12_000_000_000, "sector":"Industrials", "industry":"Aerospace", "headline":"Space launch and defense contract watch"},
    "LUNR": {"company":"Intuitive Machines", "price":12.80, "prev_close":11.40, "market_cap":2_000_000_000, "sector":"Industrials", "industry":"Aerospace", "headline":"Space contract and lunar mission catalyst"},
    "ASTS": {"company":"AST SpaceMobile", "price":48.00, "prev_close":45.50, "market_cap":18_000_000_000, "sector":"Communication Services", "industry":"Telecom", "headline":"Satellite-to-phone constellation catalyst"},
    "SOUN": {"company":"SoundHound AI", "price":11.20, "prev_close":10.20, "market_cap":4_100_000_000, "sector":"Technology", "industry":"Software", "headline":"Voice AI product expansion"},
}


def _recent_business_days(n: int = 70) -> list[pd.Timestamp]:
    end = pd.Timestamp(datetime.utcnow().date())
    return list(pd.bdate_range(end=end, periods=n))


def _make_history(ticker: str, price: float, prev_close: float, seed: int) -> pd.DataFrame:
    rng = random.Random(seed)
    dates = _recent_business_days(70)
    start = max(0.5, prev_close * rng.uniform(0.75, 1.05))
    vals = []
    cur = start
    for d in dates:
        drift = (prev_close / start) ** (1 / 65) - 1 if start > 0 else 0
        shock = rng.uniform(-0.025, 0.03)
        cur = max(0.4, cur * (1 + drift + shock))
        high = cur * rng.uniform(1.005, 1.055)
        low = cur * rng.uniform(0.945, 0.995)
        open_ = cur * rng.uniform(0.975, 1.025)
        vol = rng.randint(150_000, 2_500_000)
        vals.append({"date": d.date(), "ticker": ticker, "open": open_, "high": high, "low": low, "close": cur, "volume": vol})
    vals[-1]["open"] = prev_close * rng.uniform(0.98, 1.08)
    vals[-1]["close"] = price
    vals[-1]["high"] = max(price, vals[-1]["open"]) * rng.uniform(1.01, 1.12)
    vals[-1]["low"] = min(price, vals[-1]["open"]) * rng.uniform(0.90, 0.99)
    vals[-1]["volume"] = rng.randint(900_000, 35_000_000)
    return pd.DataFrame(vals)


def fetch_sample_prices(tickers: Iterable[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    profiles = []
    histories = []
    for idx, ticker in enumerate(tickers):
        t = str(ticker).upper().strip()
        p = SAMPLE_PROFILES.get(t)
        if p is None:
            base = 10 + idx
            p = {"company": t, "price": base * 1.03, "prev_close": base, "market_cap": 500_000_000, "sector":"Unknown", "industry":"Unknown", "headline":"No sample catalyst"}
        profiles.append({"ticker": t, **p, "data_source": "sample"})
        histories.append(_make_history(t, p["price"], p["prev_close"], idx + 17))
    return pd.DataFrame(profiles), pd.concat(histories, ignore_index=True)


def _safe_info(obj) -> dict:
    try:
        return obj.get_info() or {}
    except Exception:
        try:
            return obj.info or {}
        except Exception:
            return {}


def _fast_value(obj, key: str, default=None):
    try:
        fast = getattr(obj, "fast_info", {}) or {}
        return fast.get(key, default)
    except Exception:
        return default


def _normalise_history(hist: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if hist is None or hist.empty:
        return pd.DataFrame(columns=["date", "ticker", "open", "high", "low", "close", "volume"])
    h = hist.reset_index().copy()
    date_col = "Date" if "Date" in h.columns else "Datetime" if "Datetime" in h.columns else h.columns[0]
    h = h.rename(columns={date_col: "date", "Open":"open", "High":"high", "Low":"low", "Close":"close", "Volume":"volume"})
    h["ticker"] = ticker
    for c in ["open", "high", "low", "close", "volume"]:
        h[c] = pd.to_numeric(h[c], errors="coerce")
    return h[["date", "ticker", "open", "high", "low", "close", "volume"]].dropna(subset=["close"])


def fetch_yfinance_prices(tickers: Iterable[str], include_benchmarks: bool = True, max_tickers: int | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    try:
        import yfinance as yf
    except Exception as exc:
        raise RuntimeError("yfinance is not installed. Run `pip install -r requirements.txt` or use --mode sample.") from exc

    unique = []
    for t in tickers:
        s = str(t).upper().strip()
        if s and s not in unique:
            unique.append(s)
    if max_tickers:
        unique = unique[:max_tickers]
    profile_tickers = unique[:]
    fetch_tickers = unique[:]
    for b in ["SPY", "QQQ"]:
        if include_benchmarks and b not in fetch_tickers:
            fetch_tickers.append(b)

    rows = []
    histories = []
    errors = []
    for t in fetch_tickers:
        try:
            obj = yf.Ticker(t)
            hist = obj.history(period="4mo", interval="1d", auto_adjust=False)
            h = _normalise_history(hist, t)
            if h.empty:
                errors.append({"ticker": t, "fetch_error": "empty_history"})
                continue
            histories.append(h)
            if t not in profile_tickers:
                continue
            info = _safe_info(obj)
            last_close = float(h["close"].iloc[-1])
            prev_close = float(h["close"].iloc[-2]) if len(h) > 1 else last_close
            market_cap = info.get("marketCap") or _fast_value(obj, "market_cap")
            rows.append({"ticker": t, "company": info.get("shortName") or info.get("longName") or t, "price": last_close, "prev_close": prev_close, "market_cap": market_cap, "sector": info.get("sector", "Unknown"), "industry": info.get("industry", "Unknown"), "headline": "", "data_source": "yfinance"})
        except Exception as exc:
            errors.append({"ticker": t, "fetch_error": str(exc)[:180]})
            continue

    if not rows:
        raise RuntimeError("No profile price data fetched. Check internet/API availability or use --mode sample.")
    profile = pd.DataFrame(rows)
    history = pd.concat(histories, ignore_index=True) if histories else pd.DataFrame()
    if errors:
        profile.attrs["fetch_errors"] = errors
    return profile, history


def fetch_yfinance_history_only(tickers: Iterable[str], period: str = "1mo", max_tickers: int | None = None, chunk_size: int = 80) -> pd.DataFrame:
    try:
        import yfinance as yf
    except Exception as exc:
        raise RuntimeError("yfinance is not installed. Run `pip install -r requirements.txt`.") from exc
    unique = []
    for t in tickers:
        s = str(t).upper().strip().replace(".", "-")
        if s and s not in unique:
            unique.append(s)
    if max_tickers:
        unique = unique[:max_tickers]
    histories = []
    for i in range(0, len(unique), chunk_size):
        chunk = unique[i:i + chunk_size]
        try:
            data = yf.download(" ".join(chunk), period=period, interval="1d", group_by="ticker", auto_adjust=False, threads=True, progress=False)
        except Exception:
            data = pd.DataFrame()
        if data is None or data.empty:
            continue
        if len(chunk) == 1:
            histories.append(_normalise_history(data, chunk[0]))
            continue
        for t in chunk:
            try:
                if t in data.columns.get_level_values(0):
                    h = data[t]
                    nh = _normalise_history(h, t)
                    if not nh.empty:
                        histories.append(nh)
            except Exception:
                continue
    return pd.concat(histories, ignore_index=True) if histories else pd.DataFrame(columns=["date", "ticker", "open", "high", "low", "close", "volume"])
