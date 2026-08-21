from __future__ import annotations

import hashlib
import json
from typing import Any


VALID_HORIZONS = {"5D", "10D", "20D"}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _hash12(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()[:12]


def review_closed_prediction(closed_result: dict[str, Any], outcome: dict[str, Any]) -> dict[str, Any]:
    """Review one frozen official prediction without altering the past prediction.

    outcome must provide explicit point-in-time review data and an upstream-determined
    actual_winner_tickers set. This module diagnoses capture/failure stages; it does
    not invent an "actual winner" definition after seeing results.
    """
    if closed_result.get("state") != "CLOSED" or closed_result.get("official_prediction") is not True:
        raise ValueError("review requires CLOSED official prediction")

    prediction = closed_result.get("prediction") or {}
    run_id = prediction.get("run", {}).get("run_id")
    if not run_id:
        raise ValueError("prediction run_id missing")

    horizon = str(outcome.get("horizon", "")).upper()
    if horizon not in VALID_HORIZONS:
        raise ValueError(f"horizon must be one of {sorted(VALID_HORIZONS)}")
    if outcome.get("run_id") != run_id:
        raise ValueError("review run_id mismatch")

    benchmark_return = outcome.get("benchmark_return_pct")
    if benchmark_return is None:
        raise ValueError("benchmark_return_pct missing")
    benchmark_return = float(benchmark_return)

    ticker_returns = outcome.get("ticker_total_return_pct")
    if not isinstance(ticker_returns, dict) or not ticker_returns:
        raise ValueError("ticker_total_return_pct missing")

    winners = outcome.get("actual_winner_tickers")
    if not isinstance(winners, list) or not winners:
        raise ValueError("actual_winner_tickers must be explicit and non-empty")
    winners = [str(t).upper().strip() for t in winners]

    top20_rows = prediction.get("top20") or []
    top20 = {str(row["ticker"]).upper(): row for row in top20_rows}
    top5 = {str(t).upper() for t in prediction.get("top5_tickers", [])}
    if len(top20) != 20 or len(top5) != 5:
        raise ValueError("frozen prediction Top20/Top5 contract broken")

    prediction_rows = []
    for ticker, row in top20.items():
        if ticker not in ticker_returns:
            raise ValueError(f"missing realized return for Top20 ticker {ticker}")
        ret = float(ticker_returns[ticker])
        prediction_rows.append({
            "review_id": f"REV-{run_id}-{horizon}-PRED-{ticker}",
            "run_id": run_id,
            "horizon": horizon,
            "ticker": ticker,
            "top20_rank": int(row["top20_rank"]),
            "top5_rank": row.get("top5_rank"),
            "return_pct": ret,
            "benchmark_return_pct": benchmark_return,
            "relative_alpha_pct": round(ret - benchmark_return, 8),
        })

    winner_rows = []
    failure_counts = {"DETECTION": 0, "COMPRESSION": 0, "CAPTURED_TOP5": 0}
    for ticker in winners:
        if ticker not in ticker_returns:
            raise ValueError(f"missing realized return for actual winner {ticker}")
        if ticker not in top20:
            stage = "DETECTION"
        elif ticker not in top5:
            stage = "COMPRESSION"
        else:
            stage = "CAPTURED_TOP5"
        failure_counts[stage] += 1
        winner_rows.append({
            "review_id": f"REV-{run_id}-{horizon}-WINNER-{ticker}",
            "run_id": run_id,
            "horizon": horizon,
            "ticker": ticker,
            "return_pct": float(ticker_returns[ticker]),
            "capture_stage": stage,
            "was_top20": ticker in top20,
            "was_top5": ticker in top5,
        })

    top20_recall = sum(1 for t in winners if t in top20) / len(winners)
    top5_recall = sum(1 for t in winners if t in top5) / len(winners)
    review = {
        "run_id": run_id,
        "horizon": horizon,
        "prediction_hash": closed_result.get("prediction_hash"),
        "benchmark_return_pct": benchmark_return,
        "actual_winner_tickers": winners,
        "actual_winner_recall_top20": round(top20_recall, 8),
        "actual_winner_recall_top5": round(top5_recall, 8),
        "failure_counts": failure_counts,
        "prediction_rows": prediction_rows,
        "winner_rows": winner_rows,
        "source_ref": outcome.get("source_ref"),
        "corporate_action_check": outcome.get("corporate_action_check"),
    }
    if not review["source_ref"]:
        raise ValueError("review source_ref missing")
    if review["corporate_action_check"] != "PASS":
        raise ValueError("corporate action integrity must PASS")

    review["review_hash"] = hashlib.sha256(_canonical(review).encode("utf-8")).hexdigest()
    return review


def learning_governor(reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Emit TESTING-eligible hypotheses only after recurring Forward evidence.

    This never changes an ACTIVE rule. It only creates a versioned proposal when the
    same failure stage appears in at least three distinct run IDs.
    """
    stage_runs: dict[str, set[str]] = {"DETECTION": set(), "COMPRESSION": set()}
    for review in reviews:
        run_id = str(review.get("run_id", ""))
        counts = review.get("failure_counts", {})
        if not run_id:
            continue
        for stage in stage_runs:
            if int(counts.get(stage, 0)) > 0:
                stage_runs[stage].add(run_id)

    proposals = []
    for stage, run_ids in sorted(stage_runs.items()):
        if len(run_ids) < 3:
            continue
        hypothesis = {
            "failure_stage": stage,
            "independent_run_count": len(run_ids),
            "primary_lineage_refs": sorted(run_ids),
            "status": "TESTING_ELIGIBLE_NOT_APPLIED",
            "action": (
                "Research detector recall and missing discovery axes"
                if stage == "DETECTION"
                else "Research Top5 compression anchors and false-negative causes"
            ),
        }
        hypothesis["growth_id"] = f"GRW-REVIEW-{_hash12(hypothesis)}"
        proposals.append(hypothesis)
    return proposals
