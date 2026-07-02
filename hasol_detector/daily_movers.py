from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import pandas as pd


@dataclass
class MoverConfig:
    lookback_days: int = 14
    top_n: int = 20
    min_close: float = 1.0
    min_volume: int = 100000
    min_dollar_volume: float = 1000000.0


def normalize_history(history: pd.DataFrame) -> pd.DataFrame:
    h = history.copy()
    h["ticker"] = h["ticker"].astype(str).str.upper().str.strip()
    h["date"] = pd.to_datetime(h["date"], errors="coerce").dt.date.astype(str)
    for col in ["open", "high", "low", "close", "volume"]:
        h[col] = pd.to_numeric(h[col], errors="coerce")
    h = h.dropna(subset=["ticker", "date", "close"])
    h = h.sort_values(["ticker", "date"])
    return h


def build_daily_movers(history: pd.DataFrame, cfg: MoverConfig | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    cfg = cfg or MoverConfig()
    h = normalize_history(history)
    h["prev_close"] = h.groupby("ticker")["close"].shift(1)
    h["return_1d"] = (h["close"] / h["prev_close"] - 1.0) * 100.0
    h["gap_pct"] = (h["open"] / h["prev_close"] - 1.0) * 100.0
    h["intraday_return_pct"] = (h["close"] / h["open"] - 1.0) * 100.0
    h["dollar_volume"] = h["close"] * h["volume"]
    h = h.dropna(subset=["return_1d", "prev_close"])
    dates = sorted(h["date"].unique())[-cfg.lookback_days:]
    h = h[h["date"].isin(dates)]
    raw = []
    tradable = []
    for d in dates:
        day = h[h["date"] == d].copy().sort_values("return_1d", ascending=False)
        day["rank"] = range(1, len(day) + 1)
        raw.append(day.head(cfg.top_n))
        ok = day[(day["close"] >= cfg.min_close) & (day["volume"] >= cfg.min_volume) & (day["dollar_volume"] >= cfg.min_dollar_volume)].copy()
        ok["rank"] = range(1, len(ok) + 1)
        tradable.append(ok.head(cfg.top_n))
    return pd.concat(raw, ignore_index=True) if raw else pd.DataFrame(), pd.concat(tradable, ignore_index=True) if tradable else pd.DataFrame()


def write_daily_mover_outputs(raw: pd.DataFrame, tradable: pd.DataFrame, output_dir: str) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    raw_path = out / "daily_top20_gainers_14d.csv"
    tradable_path = out / "daily_top20_tradable_gainers_14d.csv"
    meta_path = out / "daily_mover_metadata.json"
    raw.to_csv(raw_path, index=False)
    tradable.to_csv(tradable_path, index=False)
    meta = {
        "raw_rows": int(len(raw)),
        "tradable_rows": int(len(tradable)),
        "date_count": int(raw["date"].nunique()) if not raw.empty else 0,
        "top_n": 20,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "daily_top20_gainers_14d.csv": str(raw_path),
        "daily_top20_tradable_gainers_14d.csv": str(tradable_path),
        "daily_mover_metadata.json": str(meta_path),
    }
