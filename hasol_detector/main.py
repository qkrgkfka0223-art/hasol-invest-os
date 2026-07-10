from __future__ import annotations
import argparse
from .config import HasolConfig, VERSION
from .candidate_builder import build_candidate_pool, attach_candidate_context
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
from .daily_movers import MoverConfig, build_daily_movers, write_daily_mover_outputs
from .capture_analyzer import analyze_capture


def run(
    mode: str = "sample",
    universe_csv: str | None = None,
    output_dir: str = "output",
    market_code: str = "SOFT_GO",
    market_reason: str = "selective risk-on; web validation required",
    allow_execution_candidates: bool = False,
    max_tickers: int | None = None,
    external_candidates_csv: str | None = None,
    include_seed_sources: bool = True,
    build_movers: bool = False,
    mover_lookback_days: int = 14,
):
    config = HasolConfig()
    if mode not in {"sample", "live"}:
        raise ValueError("mode must be 'sample' or 'live'")

    candidate_pool = build_candidate_pool(
        universe_csv=universe_csv,
        external_candidates_csv=external_candidates_csv,
        include_seed_sources=include_seed_sources,
    )
    tickers = candidate_pool["ticker"].tolist()
    if max_tickers is None:
        max_tickers = config.max_live_tickers

    if mode == "sample":
        profile_df, history_df = fetch_sample_prices(tickers)
    else:
        profile_df, history_df = fetch_yfinance_prices(tickers, include_benchmarks=True, max_tickers=max_tickers)

    profile_df = attach_candidate_context(profile_df, candidate_pool)
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
    metadata["external_candidates_csv"] = external_candidates_csv or "none"
    metadata["candidate_pool_count"] = int(len(candidate_pool))
    metadata["candidate_sources"] = sorted(set(";".join(candidate_pool.get("candidate_source", [] ).astype(str).tolist()).split(";"))) if not candidate_pool.empty else []
    metadata["event_tagged_count"] = int((scored.get("event_tags", "NONE").astype(str) != "NONE").sum()) if not scored.empty else 0
    metadata["event_tag_none_count"] = int((scored.get("event_tags", "NONE").astype(str) == "NONE").sum()) if not scored.empty else 0
    metadata["execution_policy"] = "LOCKED_UNTIL_WEB_VALIDATION"

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

    if build_movers:
        mover_cfg = MoverConfig(lookback_days=mover_lookback_days, top_n=20)
        raw_movers, tradable_movers = build_daily_movers(history_df, mover_cfg)
        mover_paths = write_daily_mover_outputs(raw_movers, tradable_movers, output_dir)
        paths.update(mover_paths)
        capture_paths = analyze_capture(mover_paths["daily_top20_gainers_14d.csv"], output_dir, output_dir)
        paths.update(capture_paths)
        metadata["daily_mover_rows"] = int(len(raw_movers))
        metadata["daily_mover_date_count"] = int(raw_movers["date"].nunique()) if not raw_movers.empty else 0

    return {"paths": paths, "top20": top20, "top5": top5, "execution": execution, "rejected": rejected, "metadata": metadata}


def main():
    parser = argparse.ArgumentParser(description=f"HASOL_DETECTOR_V{VERSION}: candidate-builder first US stock detection engine")
    parser.add_argument("--mode", choices=["sample", "live"], default="sample")
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--universe-csv", default=None)
    parser.add_argument("--external-candidates-csv", default=None)
    parser.add_argument("--no-seed-sources", action="store_true", help="Use only universe/external CSV candidates; disable v1.4 seed sources")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--market-code", default="SOFT_GO", choices=["GO", "SOFT_GO", "NO_TRADE"])
    parser.add_argument("--market-reason", default="selective risk-on; web validation required")
    parser.add_argument("--max-tickers", type=int, default=None)
    parser.add_argument("--allow-execution-candidates", action="store_true")
    parser.add_argument("--build-movers", action="store_true", help="Build daily Top20 mover files and capture report from fetched history")
    parser.add_argument("--mover-lookback-days", type=int, default=14)
    args = parser.parse_args()
    mode = "sample" if args.sample else args.mode
    result = run(
        mode=mode,
        universe_csv=args.universe_csv,
        output_dir=args.output_dir,
        market_code=args.market_code,
        market_reason=args.market_reason,
        allow_execution_candidates=args.allow_execution_candidates,
        max_tickers=args.max_tickers,
        external_candidates_csv=args.external_candidates_csv,
        include_seed_sources=not args.no_seed_sources,
        build_movers=args.build_movers,
        mover_lookback_days=args.mover_lookback_days,
    )
    print(f"HASOL_DETECTOR_V{VERSION} | mode={mode} | market={args.market_code}")
    print(f"Candidate pool: {result['metadata'].get('candidate_pool_count')} | event-tagged: {result['metadata'].get('event_tagged_count')}")
    if args.build_movers:
        print(f"Daily movers: rows={result['metadata'].get('daily_mover_rows')} | dates={result['metadata'].get('daily_mover_date_count')}")
    print("Top5")
    top5_cols = [c for c in ["ticker", "company", "cap_bucket", "candidate_source", "source_count", "event_tags", "axis_tags", "post_spike_stage", "review_lock_reason", "change_pct", "relative_volume", "total_score", "data_quality_status"] if c in result["top5"].columns]
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
