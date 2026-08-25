from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from .alpaca_client import AlpacaClient
from .artifacts import write_run_artifacts
from .config import FEATURE_SPEC_VERSION, RANK_SPEC_VERSION, Settings
from .features import build_features
from .ranker import rank_universe, top_n
from .universe import apply_market_liquidity_gate, build_tradable_universe, load_reference_universe

NY = ZoneInfo("America/New_York")


def _iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def completed_session_end_utc(now_utc: datetime) -> datetime:
    """Return an end timestamp that never includes an in-progress US regular session.

    Before 16:20 ET, cap the request immediately before the current ET calendar day.
    Weekends/holidays are harmless because Alpaca simply returns the last completed bar.
    After 16:20 ET, the current regular session is considered completed and may be used.
    """
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    now_et = now_utc.astimezone(NY)
    if now_et.timetz().replace(tzinfo=None) < time(16, 20):
        start_today_et = datetime.combine(now_et.date(), time(0, 0), tzinfo=NY)
        return (start_today_et - timedelta(microseconds=1)).astimezone(timezone.utc)
    return now_utc.astimezone(timezone.utc)


def run_full_market_quant(output_dir: Path, feed: str = "sip", lookback_calendar_days: int = 120, end_utc: datetime | None = None) -> dict:
    settings = Settings.from_env(feed=feed)
    client = AlpacaClient(settings)
    requested_now = end_utc or datetime.now(timezone.utc)
    data_end_utc = completed_session_end_utc(requested_now)
    start_utc = data_end_utc - timedelta(days=lookback_calendar_days)

    reference = load_reference_universe()
    assets = client.list_active_assets()
    base_universe = build_tradable_universe(reference, assets)
    symbols = sorted(set(base_universe["ticker"].tolist()) | {"SPY"})
    bars = client.fetch_daily_bars(symbols=symbols, start_iso=_iso_utc(start_utc), end_iso=_iso_utc(data_end_utc), adjustment="all")
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
        "requested_symbols": requested,
        "returned_symbols": returned,
        "coverage_pct": coverage,
        "missing_symbol_count": len(missing_symbols),
        "missing_symbols": missing_symbols,
        "reference_non_etf_count": int(reference["ticker"].nunique()),
        "alpaca_tradable_intersection_count": int(base_universe["ticker"].nunique()),
        "eligible_universe_count": int(len(eligible_set)),
        "bar_rows": int(len(bars)),
        "feed": feed,
        "feature_spec_version": FEATURE_SPEC_VERSION,
        "rank_spec_version": RANK_SPEC_VERSION,
    }
    if coverage < 0.98:
        raise RuntimeError(f"Coverage gate failed: {coverage:.2%} < 98%. Artifacts are not official.")
    if len(top50) < 50:
        raise RuntimeError(f"Ranking gate failed: only {len(top50)} valid ranked candidates.")

    run_id = f"QUANT-{data_end_utc.strftime('%Y%m%dT%H%M%SZ')}-{RANK_SPEC_VERSION}"
    manifest = {
        "run_id": run_id,
        "created_at_utc": _iso_utc(datetime.now(timezone.utc)),
        "requested_at_utc": _iso_utc(requested_now),
        "market_data_start_utc": _iso_utc(start_utc),
        "market_data_end_utc": _iso_utc(data_end_utc),
        "completed_session_cutoff_rule": "before 16:20 ET exclude current ET day; after 16:20 ET allow current completed session",
        "feed": feed,
        "adjustment": "all",
        "feature_spec_version": FEATURE_SPEC_VERSION,
        "rank_spec_version": RANK_SPEC_VERSION,
        "git_sha": os.getenv("GITHUB_SHA"),
        "git_ref": os.getenv("GITHUB_REF"),
        "workflow_run_id": os.getenv("GITHUB_RUN_ID"),
        "data_quality": data_quality,
    }
    write_run_artifacts(Path(output_dir), eligible, features[features["ticker"].isin(eligible_set)].copy(), ranked, top50, data_quality, manifest)
    return manifest
