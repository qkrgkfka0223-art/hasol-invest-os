from __future__ import annotations
import argparse
from .config import HasolConfig, VERSION
from .universe import load_universe
from .price_fetcher import fetch_sample_prices, fetch_yfinance_prices
from .feature_builder import build_features
from .sec_scanner import scan_sec_events
from .catalyst_tagger import tag_catalysts
from .cap_bucket import add_cap_bucket, select_top20_by_cap_bucket
from .stage_classifier import add_post_spike_stage
from .data_quality import add_data_quality_flags, build_run_metadata
from .ranker import score_candidates, select_top5, select_execution_candidates
from .validator import apply_kill_rules
from .exporter import export_results


def run(
    mode: str = "sample",
    universe_csv: str | None = None,
    output_dir: str = "output",
    market_code: str = "SOFT_GO",
    market_reason: str = "selective risk-on; web validation required",
    allow_execution_candidates: bool = False,
    max_tickers: int | None = None,
):
    config = HasolConfig()
    if mode not in {"sample", "live"}:
        raise ValueError("mode must be 'sample' or 'live'")

    universe = load_universe(universe_csv)
    tickers = universe["ticker"].tolist()
    if max_tickers is None:
        max_tickers = config.max_live_tickers

    if mode == "sample":
        profile_df, history_df = fetch_sample_prices(tickers)
    else:
        profile_df, history_df = fetch_yfinance_prices(tickers, include_benchmarks=True, max_tickers=max_tickers)

    features = build_features(profile_df, history_df)
    quality = add_data_quality_flags(features, data_mode=mode, config=config)
    sec_events = scan_sec_events(tickers, sample=(mode == "sample"))
    tagged = tag_catalysts(quality, sec_events)
    bucketed = add_cap_bucket(tagged, config)
    staged = add_post_spike_stage(bucketed)
    scored = score_candidates(staged, market_code=market_code, config=config)
    filtered, rejected = apply_kill_rules(scored, market_code=market_code, config=config)
    top20 = select_top20_by_cap_bucket(filtered, config)
    top5 = select_top5(top20)
    execution = select_execution_candidates(
        top5,
        market_code=market_code,
        data_mode=mode,
        allow_execution=allow_execution_candidates,
    )

    metadata = build_run_metadata(
        raw=staged,
        scored=scored,
        top20=top20,
        top5=top5,
        data_mode=mode,
        market_code=market_code,
        allow_execution=allow_execution_candidates,
    )
    metadata["market_reason"] = market_reason
    metadata["universe_csv"] = universe_csv or "built_in_sample_universe"

    paths = export_results(
        output_dir=output_dir,
        raw=staged,
        scored=scored,
        filtered=filtered,
        rejected=rejected,
        top20=top20,
        top5=top5,
        execution=execution,
        market_code=market_code,
        market_reason=market_reason,
        data_mode=mode,
        run_metadata=metadata,
    )
    return {"paths": paths, "top20": top20, "top5": top5, "execution": execution, "rejected": rejected, "metadata": metadata}


def main():
    parser = argparse.ArgumentParser(description=f"HASOL_DETECTOR_V{VERSION}: event-first US stock detection engine")
    parser.add_argument("--mode", choices=["sample", "live"], default="sample")
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--universe-csv", default=None)
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--market-code", default="SOFT_GO", choices=["GO", "SOFT_GO", "NO_TRADE"])
    parser.add_argument("--market-reason", default="selective risk-on; web validation required")
    parser.add_argument("--max-tickers", type=int, default=None)
    parser.add_argument("--allow-execution-candidates", action="store_true")
    args = parser.parse_args()
    mode = "sample" if args.sample else args.mode
    result = run(mode=mode, universe_csv=args.universe_csv, output_dir=args.output_dir, market_code=args.market_code, market_reason=args.market_reason, allow_execution_candidates=args.allow_execution_candidates, max_tickers=args.max_tickers)
    print(f"HASOL_DETECTOR_V{VERSION} | mode={mode} | market={args.market_code}")
    print("Top5")
    top5_cols = [c for c in ["ticker", "company", "cap_bucket", "event_tags", "axis_tags", "post_spike_stage", "review_lock_reason", "change_pct", "relative_volume", "total_score", "data_quality_status"] if c in result["top5"].columns]
    print(result["top5"][top5_cols].to_string(index=False))
    print("\nExecution candidates")
    if result["execution"].empty:
        print("none / locked until live plus manual unlock plus web validation")
    else:
        print(result["execution"][["ticker", "price", "total_score", "execution_reason"]].to_string(index=False))
    print("\nOutput files")
    for k, v in result["paths"].items():
        print(f"- {k}: {v}")


if __name__ == "__main__":
    main()
