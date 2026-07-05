from __future__ import annotations

import argparse
import json
from pathlib import Path

from .daily_movers import MoverConfig, build_daily_movers, write_daily_mover_outputs
from .price_fetcher import fetch_yfinance_history_only
from .us_universe import load_us_listed_universe


def run_live_movers(output_dir: str = "output_mover_live", max_tickers: int | None = 1200, include_etfs: bool = False, lookback_days: int = 14, period: str = "1mo", sample_universe: bool = False, seed: int = 42, chunk_size: int = 80) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    universe = load_us_listed_universe(include_etfs=include_etfs, limit=max_tickers, sample=sample_universe, seed=seed)
    universe_path = out / "us_listed_universe.csv"
    universe.to_csv(universe_path, index=False)

    history = fetch_yfinance_history_only(universe["ticker"].tolist(), period=period, max_tickers=max_tickers, chunk_size=chunk_size)
    history_path = out / "mover_price_history.csv"
    history.to_csv(history_path, index=False)

    raw, tradable = build_daily_movers(history, MoverConfig(lookback_days=lookback_days, top_n=20))
    paths = write_daily_mover_outputs(raw, tradable, output_dir)
    meta = {
        "mode": "live_mover",
        "universe_source": "nasdaq_trader_symbol_directories",
        "max_tickers": max_tickers,
        "sample_universe": bool(sample_universe),
        "seed": seed,
        "chunk_size": chunk_size,
        "universe_count": int(len(universe)),
        "history_rows": int(len(history)),
        "history_ticker_count": int(history["ticker"].nunique()) if not history.empty else 0,
        "date_count": int(raw["date"].nunique()) if not raw.empty else 0,
        "raw_mover_rows": int(len(raw)),
        "tradable_mover_rows": int(len(tradable)),
        "include_etfs": bool(include_etfs),
        "period": period,
    }
    meta_path = out / "live_mover_metadata.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    paths.update({
        "us_listed_universe.csv": str(universe_path),
        "mover_price_history.csv": str(history_path),
        "live_mover_metadata.json": str(meta_path),
    })
    return paths


def main():
    parser = argparse.ArgumentParser(description="HASOL live daily mover builder")
    parser.add_argument("--output-dir", default="output_mover_live")
    parser.add_argument("--max-tickers", type=int, default=1200)
    parser.add_argument("--include-etfs", action="store_true")
    parser.add_argument("--lookback-days", type=int, default=14)
    parser.add_argument("--period", default="1mo")
    parser.add_argument("--sample-universe", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--chunk-size", type=int, default=80)
    args = parser.parse_args()
    max_tickers = None if args.max_tickers <= 0 else args.max_tickers
    paths = run_live_movers(
        output_dir=args.output_dir,
        max_tickers=max_tickers,
        include_etfs=args.include_etfs,
        lookback_days=args.lookback_days,
        period=args.period,
        sample_universe=args.sample_universe,
        seed=args.seed,
        chunk_size=args.chunk_size,
    )
    print("HASOL live mover outputs")
    for k, v in paths.items():
        print(f"- {k}: {v}")


if __name__ == "__main__":
    main()
