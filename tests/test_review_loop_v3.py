from __future__ import annotations

from hasol_runtime import HasolRuntime
from hasol_runtime.review import learning_governor, review_closed_prediction
from tests.test_model_loop_v3 import make_payload


def make_closed_result():
    result = HasolRuntime(make_payload()).run()
    return HasolRuntime.close_after_readback(result, result["prediction_hash"])


def make_review(closed, run_id: str | None = None):
    prediction = closed["prediction"]
    original_run_id = prediction["run"]["run_id"]
    if run_id and run_id != original_run_id:
        prediction["run"]["run_id"] = run_id
    effective_run_id = prediction["run"]["run_id"]

    top20 = [row["ticker"] for row in prediction["top20"]]
    top5 = prediction["top5_tickers"]
    all_names = [f"T{i:02d}" for i in range(25)]
    outside = next(t for t in all_names if t not in top20)
    compression_miss = next(t for t in top20 if t not in top5)
    captured = top5[0]

    returns = {ticker: float(idx) for idx, ticker in enumerate(top20, 1)}
    returns[outside] = 40.0

    outcome = {
        "run_id": effective_run_id,
        "horizon": "5D",
        "benchmark_return_pct": 1.0,
        "ticker_total_return_pct": returns,
        "actual_winner_tickers": [outside, compression_miss, captured],
        "source_ref": f"market://review/{effective_run_id}/5D",
        "corporate_action_check": "PASS",
    }
    return review_closed_prediction(closed, outcome)


def test_review_separates_detection_compression_and_capture():
    closed = make_closed_result()
    review = make_review(closed)
    assert review["failure_counts"]["DETECTION"] == 1
    assert review["failure_counts"]["COMPRESSION"] == 1
    assert review["failure_counts"]["CAPTURED_TOP5"] == 1
    assert len(review["prediction_rows"]) == 20
    assert len(review["winner_rows"]) == 3
    assert review["review_hash"]


def test_learning_governor_requires_three_independent_runs():
    reviews = []
    for idx in range(3):
        closed = make_closed_result()
        new_run = f"RUN-202608{19 + idx:02d}-CLOSE-P11-R10"
        closed["prediction"]["run"]["run_id"] = new_run
        reviews.append(make_review(closed))

    two = learning_governor(reviews[:2])
    assert two == []

    three = learning_governor(reviews)
    stages = {p["failure_stage"] for p in three}
    assert stages == {"DETECTION", "COMPRESSION"}
    assert all(p["status"] == "TESTING_ELIGIBLE_NOT_APPLIED" for p in three)


def test_review_rejects_unofficial_prediction():
    result = HasolRuntime(make_payload()).run()
    top20 = [row["ticker"] for row in result["prediction"]["top20"]]
    outcome = {
        "run_id": result["prediction"]["run"]["run_id"],
        "horizon": "5D",
        "benchmark_return_pct": 0.0,
        "ticker_total_return_pct": {t: 1.0 for t in top20},
        "actual_winner_tickers": [top20[0]],
        "source_ref": "market://test",
        "corporate_action_check": "PASS",
    }
    try:
        review_closed_prediction(result, outcome)
        assert False, "unofficial prediction must not be reviewed as official"
    except ValueError as exc:
        assert "CLOSED official prediction" in str(exc)
