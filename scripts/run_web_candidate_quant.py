from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from hasol_detector.web_event_model import SCHEMA_VERSION, normalize_payload
from hasol_quant.features import build_features
from hasol_quant.ranker import rank_universe, top_n
from hasol_quant.yahoo_client import fetch_daily_bars

ENGINE = "HASOL-WEB-CANDIDATE-QUANT-v2.2"
DATA_SOURCE = "YAHOO_YFINANCE_DETECTION_ONLY"
FINAL_VALIDATOR = "ALPACA_CONNECTED_APP"
TOP20_CONTRACT = "HASOL-TOP20-EXACT-v1"
MIN_FREEZE_CANDIDATES = 20
CANDIDATE_BREADTH_TARGET = 20
MIN_MARKET_DATA_COVERAGE = 0.80
BACKSTOP_WATCHLIST_PATH = Path("data/candidate_universe.csv")


def _load(path: Path) -> tuple[dict, dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    normalized = normalize_payload(raw)
    return raw, normalized


def _prediction_date(payload: dict) -> date:
    raw = payload.get("prediction_date_et")
    if raw:
        return date.fromisoformat(raw)
    return datetime.now(ZoneInfo("America/New_York")).date()


def _input_hash(payload: dict) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _candidate_frame(payload: dict) -> pd.DataFrame:
    rows = []
    for item in payload.get("candidates", []):
        ticker = str(item.get("ticker", "")).upper().strip()
        if not ticker:
            continue
        row = dict(item)
        row["ticker"] = ticker
        row["provenance"] = "EVENT"
        rows.append(row)
    if not rows:
        return pd.DataFrame(columns=["ticker", "provenance"])
    return pd.DataFrame(rows).drop_duplicates(subset=["ticker"], keep="first").reset_index(drop=True)


def _load_backstop_watchlist(exclude_tickers: set[str]) -> pd.DataFrame:
    """Load the approved liquid-watchlist backstop without fabricating events.

    This is detection-only input. Final common-stock/security/tradability/freshness validation
    remains mandatory through the connected Alpaca app before checkpoint promotion.
    """
    if not BACKSTOP_WATCHLIST_PATH.exists():
        return pd.DataFrame(columns=["ticker", "provenance"])
    x = pd.read_csv(BACKSTOP_WATCHLIST_PATH, dtype=str, keep_default_na=False).fillna("")
    required = {"ticker", "execution_allowed"}
    if not required.issubset(x.columns):
        raise ValueError("approved backstop watchlist missing required columns")
    x["ticker"] = x["ticker"].astype(str).str.upper().str.strip()
    x["execution_allowed"] = x["execution_allowed"].astype(str).str.lower().str.strip()
    x = x[x["execution_allowed"].isin({"yes", "conditional"})].copy()
    x = x[(x["ticker"] != "") & (~x["ticker"].isin(exclude_tickers))].copy()
    x = x.drop_duplicates(subset=["ticker"], keep="first").reset_index(drop=True)
    if x.empty:
        return pd.DataFrame(columns=["ticker", "provenance"])
    keep = [c for c in ("ticker", "group", "axis", "watch_reason", "liquidity_bucket", "risk_bucket", "execution_allowed") if c in x.columns]
    x = x[keep].copy()
    x["provenance"] = "FULL_MARKET_QUANT_BACKSTOP"
    x["event_id"] = ""
    x["backstop_source"] = "APPROVED_LIQUID_WATCHLIST"
    return x


def _eligibility(features: pd.DataFrame) -> pd.DataFrame:
    x = features.copy()
    if x.empty:
        x["quant_eligible"] = pd.Series(dtype=bool)
        x["quant_reject_reason"] = pd.Series(dtype=str)
        return x
    reasons, eligible = [], []
    for _, row in x.iterrows():
        r = []
        if pd.isna(row.get("close")) or float(row.get("close")) < 3.0:
            r.append("PRICE_LT_3")
        if pd.isna(row.get("adv20_usd")) or float(row.get("adv20_usd")) < 10_000_000:
            r.append("ADV20_LT_10M")
        if int(row.get("history_bars") or 0) < 20:
            r.append("HISTORY_LT_20")
        eligible.append(not r)
        reasons.append("|".join(r))
    x["quant_eligible"] = eligible
    x["quant_reject_reason"] = reasons
    return x


def _event_first_rank(ranked: pd.DataFrame) -> pd.DataFrame:
    """Keep verified event candidates primary, then use Quant-ranked backstop only to fill breadth."""
    if ranked.empty:
        return ranked
    x = ranked.copy()
    x["_source_priority"] = x.get("provenance", pd.Series(index=x.index, dtype=str)).map(
        {"EVENT": 0, "FULL_MARKET_QUANT_BACKSTOP": 1}
    ).fillna(2)
    x = x.sort_values(
        by=["_source_priority", "quant_score", "adv20_usd", "ticker"],
        ascending=[True, False, False, True],
        kind="mergesort",
    ).drop(columns=["_source_priority"]).reset_index(drop=True)
    x["quant_rank"] = range(1, len(x) + 1)
    return x


def _quality(
    payload: dict,
    input_count: int,
    event_count: int,
    backstop_count: int,
    market_returned: int,
    eligible_count: int,
    ranked_count: int,
    top_count: int,
) -> dict:
    coverage = (market_returned / input_count) if input_count else 0.0
    production = bool(payload.get("eligible_for_prediction", False))
    freeze_ready = (
        production
        and eligible_count >= MIN_FREEZE_CANDIDATES
        and ranked_count >= MIN_FREEZE_CANDIDATES
        and top_count >= CANDIDATE_BREADTH_TARGET
        and coverage >= MIN_MARKET_DATA_COVERAGE
    )
    if not production:
        status = "TEST_ONLY"
    elif eligible_count == 0:
        status = "NO_PREDICTION"
    elif freeze_ready:
        status = "PASS"
    else:
        status = "DEGRADED"
    reasons = []
    if production and input_count < CANDIDATE_BREADTH_TARGET:
        reasons.append("BREADTH_BELOW_TARGET")
    if production and coverage < MIN_MARKET_DATA_COVERAGE:
        reasons.append("MARKET_DATA_COVERAGE_LOW")
    if production and eligible_count < MIN_FREEZE_CANDIDATES:
        reasons.append("QUANT_ELIGIBLE_LT_20")
    if production and ranked_count < MIN_FREEZE_CANDIDATES:
        reasons.append("RANKED_LT_20")
    if production and top_count < CANDIDATE_BREADTH_TARGET:
        reasons.append("TOP20_INCOMPLETE")
    return {
        "raw_event_count": int(payload.get("event_count_raw", 0)),
        "deduped_event_count": int(payload.get("event_count_deduped", 0)),
        "event_candidates": event_count,
        "backstop_candidates": backstop_count,
        "input_candidates": input_count,
        "candidate_breadth_target": CANDIDATE_BREADTH_TARGET,
        "breadth_warning": bool(production and eligible_count < CANDIDATE_BREADTH_TARGET),
        "market_data_returned": market_returned,
        "market_data_coverage": coverage,
        "min_market_data_coverage": MIN_MARKET_DATA_COVERAGE,
        "quant_eligible": eligible_count,
        "min_freeze_candidates": MIN_FREEZE_CANDIDATES,
        "quant_ranked": ranked_count,
        "top50_count": top_count,
        "top20_contract": TOP20_CONTRACT,
        "quality_status": status,
        "freeze_ready": freeze_ready,
        "quality_reasons": reasons,
        "canonical_market_fact": False,
        "final_market_validation_required": True,
    }


def run(input_path: Path, output_dir: Path) -> dict:
    raw_payload, payload = _load(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    event_candidates = _candidate_frame(payload)
    production = bool(payload.get("eligible_for_prediction", False))
    event_tickers = set(event_candidates.get("ticker", pd.Series(dtype=str)).astype(str))
    backstop_candidates = _load_backstop_watchlist(event_tickers) if production and len(event_candidates) < CANDIDATE_BREADTH_TARGET else pd.DataFrame(columns=["ticker", "provenance"])
    candidates = pd.concat([event_candidates, backstop_candidates], ignore_index=True, sort=False)
    candidates = candidates.drop_duplicates(subset=["ticker"], keep="first").reset_index(drop=True)
    prediction_date = _prediction_date(payload)
    symbols = sorted(set(candidates.get("ticker", pd.Series(dtype=str)).tolist()) | {"SPY"})

    if candidates.empty:
        all_candidates = candidates.copy()
        ranked = pd.DataFrame()
        top50 = pd.DataFrame()
    else:
        bars = fetch_daily_bars(symbols, completed_before_et=prediction_date)
        features = build_features(bars) if not bars.empty else pd.DataFrame()
        candidate_features = features[features["ticker"].isin(set(candidates["ticker"]))].copy() if not features.empty else pd.DataFrame()
        candidate_features = _eligibility(candidate_features)
        all_candidates = candidates.merge(candidate_features, on="ticker", how="left")
        missing_mask = all_candidates["history_bars"].isna() if "history_bars" in all_candidates.columns else pd.Series(True, index=all_candidates.index)
        all_candidates.loc[missing_mask, "quant_eligible"] = False
        all_candidates.loc[missing_mask, "quant_reject_reason"] = "NO_MARKET_DATA"
        eligible_set = set(all_candidates.loc[all_candidates["quant_eligible"] == True, "ticker"].astype(str))  # noqa: E712
        ranked_core = rank_universe(features, eligible_tickers=eligible_set) if eligible_set else pd.DataFrame()
        meta_cols = [c for c in candidates.columns if c != "ticker"]
        ranked = ranked_core.merge(candidates[["ticker"] + meta_cols], on="ticker", how="left") if not ranked_core.empty else ranked_core
        ranked = _event_first_rank(ranked)
        top50 = top_n(ranked, 50) if not ranked.empty else ranked

    all_candidates.to_csv(output_dir / "candidate_features.csv", index=False)
    ranked.to_csv(output_dir / "web_candidate_quant.csv", index=False)
    top50.to_csv(output_dir / "quant_top50.csv", index=False)
    (output_dir / "quant_top50.json").write_text(json.dumps(top50.to_dict(orient="records"), ensure_ascii=False, default=str, indent=2), encoding="utf-8")
    (output_dir / "input_snapshot_raw.json").write_text(json.dumps(raw_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "input_snapshot_normalized.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    input_count = int(len(candidates))
    market_returned = int(all_candidates["history_bars"].notna().sum()) if input_count and "history_bars" in all_candidates.columns else 0
    eligible_count = int(all_candidates["quant_eligible"].fillna(False).sum()) if input_count and "quant_eligible" in all_candidates.columns else 0
    quality = _quality(
        payload,
        input_count,
        int(len(event_candidates)),
        int(len(backstop_candidates)),
        market_returned,
        eligible_count,
        int(len(ranked)),
        int(len(top50)),
    )
    (output_dir / "data_quality.json").write_text(json.dumps(quality, indent=2), encoding="utf-8")

    preview_cols = [c for c in ("ticker", "quant_rank", "quant_score", "adv20_usd", "provenance", "event_id", "backstop_source") if c in top50.columns]
    top20_preview = top50.head(20)[preview_cols].to_dict(orient="records") if not top50.empty else []
    manifest = {
        "engine": ENGINE,
        "schema_version": SCHEMA_VERSION,
        "input_sha256": _input_hash(raw_payload),
        "normalized_input_sha256": _input_hash(payload),
        "run_type": payload.get("run_type", "UNKNOWN"),
        "eligible_for_prediction": production,
        "prediction_date_et": prediction_date.isoformat(),
        "cutoff_et": payload.get("cutoff_et"),
        "candidate_source": "HASOL_WEB_EVENT_DETECTOR+APPROVED_LIQUID_WATCHLIST_BACKSTOP",
        "event_source_policy": "OFFICIAL_PRIMARY_REQUIRED_FOR_PRODUCTION",
        "backstop_policy": "APPROVED_LIQUID_WATCHLIST_DETECTION_ONLY_NO_FABRICATED_EVENTS",
        "quant_market_source": DATA_SOURCE,
        "quant_source_policy": "DETECTION_ONLY_NOT_CANONICAL",
        "final_market_validator": FINAL_VALIDATOR,
        "top20_contract": TOP20_CONTRACT,
        "top20_preview": top20_preview,
        "generated_at_utc": datetime.now(ZoneInfo("UTC")).isoformat(),
        "quality": quality,
    }
    (output_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    p = argparse.ArgumentParser(description="HASOL Web-first candidate Quant with approved exact-Top20 backstop (no Alpaca secret required)")
    p.add_argument("--input", default="runtime/web_candidates/latest.json")
    p.add_argument("--output-dir", default="output_web_quant")
    p.add_argument("--require-freeze-ready", action="store_true", help="Fail when a prediction-eligible input cannot produce at least 20 Quant-eligible ranked names")
    args = p.parse_args()
    manifest = run(Path(args.input), Path(args.output_dir))
    print(json.dumps(manifest, indent=2, default=str))
    if args.require_freeze_ready and manifest["eligible_for_prediction"] and not manifest["quality"]["freeze_ready"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
