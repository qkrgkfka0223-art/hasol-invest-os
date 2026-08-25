from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path

from .alpaca_client import AlpacaClient
from .artifacts import write_run_artifacts
from .config import FEATURE_SPEC_VERSION, RANK_SPEC_VERSION, Settings
from .features import build_features
from .ranker import rank_universe, top_n
from .universe import apply_market_liquidity_gate, build_tradable_universe, load_reference_universe


def _iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def run_full_market_quant(output_dir: Path, feed: str = "sip", lookback_calendar_days: int = 120, end_utc: datetime | None = None) -> dict:
    settings = Settings.from_env(feed=feed)
    client = AlpacaClient(settings)
    end_utc = end_utc or datetime.now(timezone.utc)
    start_utc = end_utc - timedelta(days=lookback_calendar_days)
    reference = load_reference_universe()
    assets = client.list_active_assets()
    base_universe = build_tradable_universe(reference, assets)
    symbols = sorted(set(base_universe["ticker"].tolist()) | {"SPY"})
    bars = client.fetch_daily_bars(symbols=symbols, start_iso=_iso_utc(start_utc), end_iso=_iso_utc(end_utc), adjustment="all")
    if bars.empty:
        raise RuntimeError("No market bars returned; refusing to create a false successful run.")
    features = build_features(bars)
    eligible = apply_market_liquidity_gate(base_universe, features)
    eligible_set = set(eligible["ticker"].tolist())
    ranked = rank_universe(features, eligible_set)
    top50 = top_n(ranked, 50)
    requested = len(symbols)
    returned = bars["ticker"].nunique()
    coverage = returned / requested if requested else 0.0
    missing_symbols = sorted(set(symbols) - set(bars["ticker"].unique()))
    data_quality = {
        "requested_symbols": requested, "returned_symbols": returned, "coverage_pct": coverage,
        "missing_symbol_count": len(missing_symbols), "missing_symbols": missing_symbols,
        "reference_non_etf_count": int(reference["ticker"].nunique()),
        "alpaca_tradable_intersection_count": int(base_universe["ticker"].nunique()),
        "eligible_universe_count": int(len(eligible_set)), "bar_rows": int(len(bars)), "feed": feed,
        "feature_spec_version": FEATURE_SPEC_VERSION, "rank_spec_version": RANK_SPEC_VERSION,
    }
    if coverage < 0.98:
        raise RuntimeError(f"Coverage gate failed: {coverage:.2%} < 98%. Artifacts are not official.")
    if len(top50) < 50:
        raise RuntimeError(f"Ranking gate failed: only {len(top50)} valid ranked candidates.")
    run_id = f"QUANT-{end_utc.strftime('%Y%m%dT%H%M%SZ')}-{RANK_SPEC_VERSION}"
    manifest = {
        "run_id": run_id, "created_at_utc": _iso_utc(datetime.now(timezone.utc)),
        "market_data_start_utc": _iso_utc(start_utc), "market_data_end_utc": _iso_utc(end_utc),
        "feed": feed, "adjustment": "all", "feature_spec_version": FEATURE_SPEC_VERSION,
        "rank_spec_version": RANK_SPEC_VERSION, "git_sha": os.getenv("GITHUB_SHA"),
        "git_ref": os.getenv("GITHUB_REF"), "workflow_run_id": os.getenv("GITHUB_RUN_ID"),
        "data_quality": data_quality,
    }
    write_run_artifacts(Path(output_dir), eligible, features[features["ticker"].isin(eligible_set)].copy(), ranked, top50, data_quality, manifest)
    return manifest
