from __future__ import annotations

import math
from statistics import median
from typing import Any

from .contracts import CONTRACT


def _percentiles(values: dict[str, float | None]) -> dict[str, float | None]:
    valid: list[tuple[float, str]] = []
    for key, value in values.items():
        if value is None:
            continue
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"{key}: engine raw value must be finite or NULL")
        valid.append((number, key))
    valid.sort()

    out: dict[str, float | None] = {k: None for k in values}
    n = len(valid)
    if n == 0:
        return out
    if n == 1:
        out[valid[0][1]] = 100.0
        return out

    i = 0
    while i < n:
        value = valid[i][0]
        j = i
        while j + 1 < n and valid[j + 1][0] == value:
            j += 1
        avg_rank = (i + j) / 2.0
        pct = 100.0 * avg_rank / (n - 1)
        for pos in range(i, j + 1):
            out[valid[pos][1]] = round(pct, 8)
        i = j + 1
    return out


def build_engine_percentiles(rows: list[dict[str, Any]]) -> None:
    """Mutates rows by adding deterministic frozen-universe engine percentiles."""
    for engine in CONTRACT.positive_engines:
        raw = {row["ticker"]: row.get("engine_raw", {}).get(engine) for row in rows}
        pcts = _percentiles(raw)
        for row in rows:
            row.setdefault("engine_percentiles", {})[engine] = pcts[row["ticker"]]


def aggregate_score(row: dict[str, Any]) -> float | None:
    pcts = row.get("engine_percentiles", {})
    valid = [float(pcts[e]) for e in CONTRACT.positive_engines if pcts.get(e) is not None]
    if len(valid) < CONTRACT.min_valid_positive_engines:
        return None
    penalty = float(row.get("risk_penalty", 0.0))
    if not math.isfinite(penalty) or penalty < 0 or penalty > 30:
        raise ValueError(f"{row.get('ticker')}: risk_penalty must be finite 0..30")
    return round(float(median(valid)) - penalty, 8)


def _tie_value(value: float | None) -> float:
    return -1.0 if value is None else float(value)


def rank_top20(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    build_engine_percentiles(rows)
    scored: list[dict[str, Any]] = []
    for row in rows:
        row["agg_score"] = aggregate_score(row)
        if row["agg_score"] is not None:
            scored.append(row)

    if len(scored) < CONTRACT.top20_count:
        raise ValueError(
            f"Need at least {CONTRACT.top20_count} rows with >= "
            f"{CONTRACT.min_valid_positive_engines}/6 valid engines; got {len(scored)}"
        )

    def key(row: dict[str, Any]):
        p = row["engine_percentiles"]
        return (
            -float(row["agg_score"]),
            -_tie_value(p.get("future_flow_event")),
            -_tie_value(p.get("earnings_expectations")),
            -float(row["adv20_usd"]),
            row["ticker"],
        )

    top = sorted(scored, key=key)[: CONTRACT.top20_count]
    for idx, row in enumerate(top, 1):
        row["top20_rank"] = idx
    return top


def compression_score(row: dict[str, Any]) -> float:
    comp = row.get("compression", {})
    vals: list[float] = []
    for name in CONTRACT.compression_components:
        value = comp.get(name)
        if value not in CONTRACT.compression_allowed_scores:
            raise ValueError(
                f"{row.get('ticker')}: compression {name}={value!r}; "
                f"allowed={CONTRACT.compression_allowed_scores}"
            )
        vals.append(float(value))
    return float(median(vals))


def rank_top5(top20: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for row in top20:
        row["compression_score"] = compression_score(row)

    ranked = sorted(
        top20,
        key=lambda r: (
            -float(r["compression_score"]),
            -float(r["agg_score"]),
            int(r["top20_rank"]),
        ),
    )[: CONTRACT.top5_count]
    for idx, row in enumerate(ranked, 1):
        row["top5_rank"] = idx
    return ranked
