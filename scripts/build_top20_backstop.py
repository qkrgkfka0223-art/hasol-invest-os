from __future__ import annotations

import argparse
import json
import os
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

from hasol_quant.alpaca_client import AlpacaClient
from hasol_quant.config import Settings
from hasol_quant.features import build_features
from hasol_quant.ranker import rank_universe
from hasol_quant.universe import is_common_equity_security_name

SCHEMA = "HASOL-TOP20-BACKSTOP-v1"
TOP20_CONTRACT = "HASOL-TOP20-EXACT-v1"
MIN_HISTORY_BARS = 61
MIN_PRICE = 3.0
MIN_ADV20_USD = 10_000_000.0


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_checkpoint(pointer_path: Path) -> tuple[dict[str, Any], str]:
    pointer = _read_json(pointer_path)
    checkpoint_path = Path(str(pointer.get("checkpoint_path", "")))
    if not checkpoint_path.is_file():
        raise RuntimeError(f"checkpoint path not found: {checkpoint_path}")
    return _read_json(checkpoint_path), checkpoint_path.as_posix()


def _event_rows(checkpoint: dict[str, Any]) -> list[dict[str, Any]]:
    top20 = [str(x).upper().strip() for x in checkpoint.get("top20", []) if str(x).strip()]
    provenance = checkpoint.get("top20_provenance")
    if isinstance(provenance, dict):
        event_tickers = [t for t in top20 if str((provenance.get(t) or {}).get("source", "")).upper() == "EVENT"]
    else:
        event_tickers = top20  # legacy thin checkpoints were event-only lists
    top5_by_ticker = {
        str(row.get("ticker", "")).upper().strip(): row
        for row in checkpoint.get("top5", [])
        if isinstance(row, dict)
    }
    rows: list[dict[str, Any]] = []
    for rank, ticker in enumerate(event_tickers[:20], start=1):
        top5 = top5_by_ticker.get(ticker, {})
        rows.append({
            "ticker": ticker,
            "rank": rank,
            "source": "EVENT",
            "score": top5.get("quant_score"),
            "event_id": top5.get("event_id"),
            "evidence_ref": f"checkpoint:{checkpoint.get('checkpoint_id')}:{ticker}",
        })
    return rows


def _load_watchlist(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, keep_default_na=False, na_filter=False)
    required = {"ticker", "group", "liquidity_bucket", "risk_bucket", "execution_allowed"}
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(f"candidate universe missing columns: {sorted(missing)}")
    frame["ticker"] = frame["ticker"].astype(str).str.upper().str.strip()
    allowed = frame["execution_allowed"].astype(str).str.lower().isin({"yes", "conditional"})
    group_ok = frame["group"].astype(str).str.upper().isin({"A", "B"})
    return frame.loc[allowed & group_ok & frame["ticker"].ne("")].drop_duplicates("ticker").copy()


def _has_alpaca_credentials() -> bool:
    return bool(os.getenv("ALPACA_API_KEY_ID", "").strip() and os.getenv("ALPACA_API_SECRET_KEY", "").strip())


def _security_verified_watchlist(client: AlpacaClient, watchlist: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    assets = client.list_active_assets()
    if assets.empty:
        raise RuntimeError("Alpaca active asset list is empty")
    assets["ticker"] = assets["ticker"].astype(str).str.upper().str.strip()
    assets["name_common_equity"] = assets["name"].map(is_common_equity_security_name)
    mask = assets["tradable"].eq(True) & assets["name_common_equity"].eq(True) & ~assets["exchange"].astype(str).str.upper().isin({"OTC"})
    verified = watchlist.merge(assets.loc[mask], on="ticker", how="inner")
    rejected = watchlist.loc[~watchlist["ticker"].isin(set(verified["ticker"]))].copy()
    return verified, rejected


def _fetch_alpaca_bars(symbols: list[str], start_iso: str, end_iso: str) -> tuple[pd.DataFrame, str, dict[str, str]]:
    errors: dict[str, str] = {}
    for feed in ("sip", "iex"):
        try:
            settings = replace(Settings.from_env(feed=feed), timeout_seconds=30, max_retries=3, batch_size=50)
            bars = AlpacaClient(settings).fetch_daily_bars(symbols, start_iso, end_iso)
            if bars.empty:
                errors[feed] = "EMPTY_BARS"
                continue
            return bars, feed.upper(), errors
        except Exception as exc:
            errors[feed] = f"{type(exc).__name__}: {exc}"[:500]
    raise RuntimeError(f"all Alpaca historical feeds failed: {errors}")


def _fetch_yfinance_bars(symbols: list[str]) -> pd.DataFrame:
    raw = yf.download(
        tickers=" ".join(symbols),
        period="6mo",
        interval="1d",
        group_by="ticker",
        auto_adjust=False,
        threads=True,
        progress=False,
    )
    if raw.empty:
        raise RuntimeError("public degraded market-data fallback returned no bars")
    rows: list[dict[str, Any]] = []
    multi = isinstance(raw.columns, pd.MultiIndex)
    for ticker in symbols:
        try:
            frame = raw[ticker].copy() if multi else raw.copy()
        except (KeyError, TypeError):
            continue
        frame = frame.dropna(how="all")
        if frame.empty or "Close" not in frame.columns:
            continue
        for stamp, row in frame.iterrows():
            close = row.get("Close")
            if pd.isna(close):
                continue
            ts = pd.Timestamp(stamp)
            if ts.tzinfo is None:
                ts = ts.tz_localize("UTC")
            else:
                ts = ts.tz_convert("UTC")
            rows.append({
                "ticker": ticker,
                "timestamp": ts,
                "open": row.get("Open"),
                "high": row.get("High"),
                "low": row.get("Low"),
                "close": close,
                "volume": row.get("Volume"),
                "trade_count": float("nan"),
                "vwap": float("nan"),
            })
    bars = pd.DataFrame(rows)
    if bars.empty:
        raise RuntimeError("public degraded fallback could not normalize bars")
    for col in ["open", "high", "low", "close", "volume", "trade_count", "vwap"]:
        bars[col] = pd.to_numeric(bars[col], errors="coerce")
    return bars.sort_values(["ticker", "timestamp"]).reset_index(drop=True)


def build(pointer_path: Path, watchlist_path: Path, allow_degraded_public_fallback: bool) -> dict[str, Any]:
    generated = datetime.now(timezone.utc)
    checkpoint, checkpoint_path = _latest_checkpoint(pointer_path)
    event_rows = _event_rows(checkpoint)
    if not event_rows:
        raise RuntimeError("no event-ranked names available from latest pre-open checkpoint")
    event_tickers = [row["ticker"] for row in event_rows]
    backstop_needed = max(0, 20 - len(event_tickers))
    if backstop_needed == 0:
        fused = event_tickers[:20]
        return {
            "schema": SCHEMA,
            "top20_contract": TOP20_CONTRACT,
            "generated_at_utc": generated.isoformat().replace("+00:00", "Z"),
            "source_checkpoint": checkpoint_path,
            "source_checkpoint_id": checkpoint.get("checkpoint_id"),
            "event_count": 20,
            "backstop_needed": 0,
            "backstop_count": 0,
            "market_data_source": "NOT_NEEDED",
            "fused_top20": fused,
            "event_rows": event_rows[:20],
            "backstop_rows": [],
            "valid_exact_top20": len(fused) == 20 and len(set(fused)) == 20,
            "promotion_eligible": True,
        }

    watchlist = _load_watchlist(watchlist_path)
    watchlist = watchlist.loc[~watchlist["ticker"].isin(set(event_tickers))].copy()

    security_mode = "ALPACA_CONNECTED_IN_ACTION"
    rejected = pd.DataFrame(columns=watchlist.columns)
    if _has_alpaca_credentials():
        asset_client = AlpacaClient(replace(Settings.from_env(feed="iex"), timeout_seconds=30, max_retries=3))
        verified, rejected = _security_verified_watchlist(asset_client, watchlist)
    else:
        if not allow_degraded_public_fallback:
            raise RuntimeError("missing Alpaca credentials and degraded public fallback is disabled")
        # Candidate-universe rows are pre-curated; final selected names still require connected Alpaca asset revalidation.
        verified = watchlist.copy()
        security_mode = "PENDING_CONNECTED_ALPACA_REVALIDATION"

    if len(verified) < backstop_needed:
        raise RuntimeError(f"watchlist too small after security gate: {len(verified)} < {backstop_needed}")

    symbols = ["SPY"] + sorted(set(verified["ticker"]))
    start_iso = (generated - timedelta(days=180)).isoformat().replace("+00:00", "Z")
    end_iso = generated.isoformat().replace("+00:00", "Z")
    feed_errors: dict[str, str] = {}
    promotion_eligible = True
    if _has_alpaca_credentials():
        try:
            bars, market_source, feed_errors = _fetch_alpaca_bars(symbols, start_iso, end_iso)
        except Exception as exc:
            if not allow_degraded_public_fallback:
                raise
            feed_errors["alpaca_all"] = f"{type(exc).__name__}: {exc}"[:500]
            bars = _fetch_yfinance_bars(symbols)
            market_source = "YFINANCE_DEGRADED_TEST_ONLY"
            promotion_eligible = False
    else:
        bars = _fetch_yfinance_bars(symbols)
        market_source = "YFINANCE_DEGRADED_TEST_ONLY"
        promotion_eligible = False

    features = build_features(bars)
    if features.empty or "SPY" not in set(features["ticker"]):
        raise RuntimeError("feature build missing SPY benchmark")

    feature_gate = features[
        features["history_bars"].ge(MIN_HISTORY_BARS)
        & features["close"].ge(MIN_PRICE)
        & features["adv20_usd"].ge(MIN_ADV20_USD)
    ].copy()
    eligible_set = set(verified["ticker"]) & set(feature_gate["ticker"])
    ranked = rank_universe(features, eligible_tickers=eligible_set)
    ranked = ranked[ranked["quant_score"].notna()].copy()
    ranked = ranked[~ranked["ticker"].isin(set(event_tickers))].copy()
    if len(ranked) < backstop_needed:
        raise RuntimeError(f"ranked backstop too small after history/liquidity/score gates: {len(ranked)} < {backstop_needed}")

    selected = ranked.head(backstop_needed).copy()
    backstop_rows: list[dict[str, Any]] = []
    for _, row in selected.iterrows():
        ticker = str(row["ticker"])
        backstop_rows.append({
            "ticker": ticker,
            "source": "FULL_MARKET_QUANT_BACKSTOP",
            "quant_rank": int(row["quant_rank"]),
            "score": float(row["quant_score"]),
            "close": float(row["close"]),
            "adv20_usd": float(row["adv20_usd"]),
            "history_bars": int(row["history_bars"]),
            "as_of_timestamp": pd.Timestamp(row["as_of_timestamp"]).isoformat(),
            "evidence_ref": f"HASOL-QR-v1.0:{market_source}:{ticker}",
        })

    fused = event_tickers + [row["ticker"] for row in backstop_rows]
    if len(fused) != 20 or len(set(fused)) != 20:
        raise RuntimeError(f"exact Top20 fusion invariant failed: count={len(fused)} unique={len(set(fused))}")

    covered = set(bars["ticker"].astype(str).str.upper())
    requested_market = set(symbols)
    coverage = len(covered & requested_market) / max(1, len(requested_market)) * 100.0
    if coverage < 80.0:
        raise RuntimeError(f"market-data coverage too low: {coverage:.2f}%")
    if security_mode != "ALPACA_CONNECTED_IN_ACTION":
        promotion_eligible = False

    return {
        "schema": SCHEMA,
        "top20_contract": TOP20_CONTRACT,
        "generated_at_utc": generated.isoformat().replace("+00:00", "Z"),
        "source_checkpoint": checkpoint_path,
        "source_checkpoint_id": checkpoint.get("checkpoint_id"),
        "prediction_date_et": checkpoint.get("prediction_date_et"),
        "event_count": len(event_tickers),
        "backstop_needed": backstop_needed,
        "backstop_count": len(backstop_rows),
        "market_data_source": market_source,
        "market_data_failover_errors": feed_errors,
        "security_validation_mode": security_mode,
        "watchlist_count": int(len(watchlist)),
        "security_candidate_count": int(len(verified)),
        "security_rejected": sorted(set(rejected["ticker"])) if not rejected.empty else [],
        "market_symbol_count_requested": len(requested_market),
        "market_symbol_count_covered": len(covered & requested_market),
        "market_data_coverage_pct": coverage,
        "ranked_backstop_count": int(len(ranked)),
        "event_rows": event_rows,
        "backstop_rows": backstop_rows,
        "fused_top20": fused,
        "valid_exact_top20": True,
        "promotion_eligible": promotion_eligible,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build deterministic HASOL exact-Top20 market backstop")
    parser.add_argument("--pointer", default="runtime/preopen_checkpoints/LATEST_VALID_PREOPEN_CHECKPOINT.json")
    parser.add_argument("--watchlist", default="data/candidate_universe.csv")
    parser.add_argument("--output", default="output_top20_backstop/result.json")
    parser.add_argument("--allow-degraded-public-fallback", action="store_true")
    args = parser.parse_args()
    result = build(Path(args.pointer), Path(args.watchlist), args.allow_degraded_public_fallback)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
