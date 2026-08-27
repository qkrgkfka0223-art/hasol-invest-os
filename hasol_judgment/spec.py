from __future__ import annotations

from typing import Any, Iterable

HASOL_JUDGMENT_VERSION = "HASOL-JUDGMENT-v1.1"

REQUIRED_TEXT_FIELDS = (
    "why_now",
    "future_capital_flow",
    "next_buyer",
    "market_missed",
    "reflection_level",
    "price_acceptance",
    "countercase",
    "invalidation",
    "chase_risk",
)

SCORE_FIELDS = (
    "event_conviction_score",
    "future_capital_flow_score",
    "next_buyer_score",
    "market_mispricing_score",
    "price_acceptance_score",
    "quant_score",
    "source_quality_score",
    "countercase_risk_score",
    "chase_risk_score",
)


def _score(value: Any, name: str) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not 0.0 <= x <= 100.0:
        raise ValueError(f"{name} must be between 0 and 100")
    return x


def validate_judgment(record: dict[str, Any]) -> dict[str, Any]:
    out = dict(record)
    ticker = str(out.get("ticker", "")).upper().strip()
    if not ticker:
        raise ValueError("ticker is required for HASOL judgment")
    out["ticker"] = ticker
    for field in REQUIRED_TEXT_FIELDS:
        if not str(out.get(field, "")).strip():
            raise ValueError(f"missing HASOL judgment field: {field}")
    for field in SCORE_FIELDS:
        out[field] = _score(out.get(field), field)
    return out


def fusion_score(record: dict[str, Any]) -> float:
    x = validate_judgment(record)
    positive = (
        0.15 * x["event_conviction_score"]
        + 0.20 * x["future_capital_flow_score"]
        + 0.10 * x["next_buyer_score"]
        + 0.15 * x["market_mispricing_score"]
        + 0.15 * x["price_acceptance_score"]
        + 0.15 * x["quant_score"]
        + 0.10 * x["source_quality_score"]
    )
    penalty = 0.08 * x["chase_risk_score"] + 0.05 * x["countercase_risk_score"]
    return round(max(0.0, min(100.0, positive - penalty)), 4)


def rank_judgments(records: Iterable[dict[str, Any]], *, top20_n: int = 20, top5_n: int = 5) -> list[dict[str, Any]]:
    """Validate, score and rank judgments with a deterministic tie-break contract.

    Tie-break order is fusion score, source quality, quant score, then ticker.  This
    prevents Top20/Top5 from changing simply because input rows arrive in a
    different order.
    """
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        x = validate_judgment(record)
        if x["ticker"] in seen:
            raise ValueError(f"duplicate judgment ticker: {x['ticker']}")
        seen.add(x["ticker"])
        x["judgment_version"] = HASOL_JUDGMENT_VERSION
        x["fusion_score"] = fusion_score(x)
        rows.append(x)
    rows.sort(
        key=lambda x: (
            -x["fusion_score"],
            -x["source_quality_score"],
            -x["quant_score"],
            x["ticker"],
        )
    )
    for idx, row in enumerate(rows, start=1):
        row["top20_rank"] = idx if idx <= top20_n else None
        row["top5_rank"] = idx if idx <= top5_n else None
    return rows
