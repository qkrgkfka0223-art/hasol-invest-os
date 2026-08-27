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

ENGINE = "HASOL-WEB-CANDIDATE-QUANT-v2"
DATA_SOURCE = "YAHOO_YFINANCE_DETECTION_ONLY"
FINAL_VALIDATOR = "ALPACA_CONNECTED_APP"


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
        rows.append(row)
    if not rows:
        return pd.DataFrame(columns=["ticker"])
    return pd.DataFrame(rows).drop_duplicates(subset=["ticker"], keep="first").reset_index(drop=True)


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


def run(input_path: Path, output_dir: Path) -> dict:
    raw_payload, payload = _load(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    candidates = _candidate_frame(payload)
    prediction_date = _prediction_date(payload)
    symbols = sorted(set(candidates.get("ticker", pd.Series(dtype=str)).tolist()) | {"SPY"})

    if candidates.empty:
        features = pd.DataFrame()
        all_candidates = candidates.copy()
        ranked = pd.DataFrame()
        top50 = pd.DataFrame()
    else:
        bars = fetch_daily_bars(symbols, completed_before_et=prediction_date)
        features = build_features(bars) if not bars.empty else pd.DataFrame()
        event_features = features[features["ticker"].isin(set(candidates["ticker"]))].copy() if not features.empty else pd.DataFrame()
        event_features = _eligibility(event_features)
        all_candidates = candidates.merge(event_features, on="ticker", how="left")
        missing_mask = all_candidates["history_bars"].isna() if "history_bars" in all_candidates.columns else pd.Series(True, index=all_candidates.index)
        all_candidates.loc[missing_mask, "quant_eligible"] = False
        all_candidates.loc[missing_mask, "quant_reject_reason"] = "NO_MARKET_DATA"
        eligible_set = set(all_candidates.loc[all_candidates["quant_eligible"] == True, "ticker"].astype(str))  # noqa: E712
        ranked_core = rank_universe(features, eligible_tickers=eligible_set) if eligible_set else pd.DataFrame()
        meta_cols = [c for c in candidates.columns if c != "ticker"]
        ranked = ranked_core.merge(candidates[["ticker"] + meta_cols], on="ticker", how="left") if not ranked_core.empty else ranked_core
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
    quality = {
        "raw_event_count": int(payload.get("event_count_raw", 0)),
        "deduped_event_count": int(payload.get("event_count_deduped", 0)),
        "input_candidates": input_count,
        "market_data_returned": market_returned,
        "market_data_coverage": (market_returned / input_count) if input_count else 1.0,
        "quant_eligible": eligible_count,
        "quant_ranked": int(len(ranked)),
        "top50_count": int(len(top50)),
        "canonical_market_fact": False,
        "final_market_validation_required": True,
    }
    (output_dir / "data_quality.json").write_text(json.dumps(quality, indent=2), encoding="utf-8")

    manifest = {
        "engine": ENGINE,
        "schema_version": SCHEMA_VERSION,
        "input_sha256": _input_hash(raw_payload),
        "normalized_input_sha256": _input_hash(payload),
        "run_type": payload.get("run_type", "UNKNOWN"),
        "eligible_for_prediction": bool(payload.get("eligible_for_prediction", False)),
        "prediction_date_et": prediction_date.isoformat(),
        "cutoff_et": payload.get("cutoff_et"),
        "candidate_source": "HASOL_WEB_EVENT_DETECTOR",
        "event_source_policy": "OFFICIAL_PRIMARY_REQUIRED_FOR_PRODUCTION",
        "quant_market_source": DATA_SOURCE,
        "quant_source_policy": "DETECTION_ONLY_NOT_CANONICAL",
        "final_market_validator": FINAL_VALIDATOR,
        "generated_at_utc": datetime.now(ZoneInfo("UTC")).isoformat(),
        "quality": quality,
    }
    (output_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    p = argparse.ArgumentParser(description="HASOL Web-first candidate Quant runner (no Alpaca secret required)")
    p.add_argument("--input", default="runtime/web_candidates/latest.json")
    p.add_argument("--output-dir", default="output_web_quant")
    args = p.parse_args()
    manifest = run(Path(args.input), Path(args.output_dir))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
