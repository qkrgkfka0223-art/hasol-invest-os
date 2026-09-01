from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "HASOL-PREOPEN-CHECKPOINT-v1"
INFORMATION_BARRIER = "ALPACA_REGULAR_OPEN"
REQUIRED_SOURCE_FAMILIES = (
    "SEC_EDGAR",
    "ISSUER_IR",
    "GLOBENEWSWIRE",
    "PRNEWSWIRE",
    "BUSINESS_WIRE",
    "ACCESS_NEWSWIRE",
    "FDA_REGULATORY",
    "EARNINGS_GUIDANCE_DIRECT",
)
ALLOWED_SOURCE_STATUS = {"ATTEMPTED", "NOT_APPLICABLE"}
SHA64 = re.compile(r"^[0-9a-f]{64}$")
SHA40 = re.compile(r"^[0-9a-f]{40}$")
TICKER = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")


def _parse_aware(value: Any, field: str) -> datetime:
    text = str(value or "").strip().replace("Z", "+00:00")
    if not text:
        raise ValueError(f"{field} is required")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"invalid {field}: {value}") from exc
    if dt.tzinfo is None:
        raise ValueError(f"{field} must be timezone-aware")
    return dt.astimezone(timezone.utc)


def _require_sha64(raw: dict[str, Any], field: str) -> None:
    value = str(raw.get(field, "")).strip().lower()
    if not SHA64.fullmatch(value):
        raise ValueError(f"{field} must be a 64-char sha256")


def validate_checkpoint(raw: dict[str, Any], *, path: Path | None = None) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("checkpoint must be a JSON object")
    if raw.get("schema") != SCHEMA:
        raise ValueError(f"schema must be {SCHEMA}")
    checkpoint_id = str(raw.get("checkpoint_id", "")).strip()
    if not checkpoint_id:
        raise ValueError("checkpoint_id is required")

    prediction_date = str(raw.get("prediction_date_et", "")).strip()
    try:
        datetime.fromisoformat(prediction_date).date()
    except ValueError as exc:
        raise ValueError("prediction_date_et must be YYYY-MM-DD") from exc

    captured = _parse_aware(raw.get("captured_at_utc"), "captured_at_utc")
    regular_open = _parse_aware(raw.get("next_regular_open_et"), "next_regular_open_et")
    session_asof = _parse_aware(raw.get("session_as_of_utc"), "session_as_of_utc")
    if captured >= regular_open:
        raise ValueError("checkpoint must be captured strictly before regular open")
    if session_asof > captured:
        raise ValueError("session_as_of_utc cannot be after checkpoint capture")
    if session_asof >= regular_open:
        raise ValueError("session_as_of_utc must be strictly before regular open")
    if raw.get("information_barrier") != INFORMATION_BARRIER:
        raise ValueError(f"information_barrier must be {INFORMATION_BARRIER}")

    source_commit = str(raw.get("source_commit", "")).strip().lower()
    if not SHA40.fullmatch(source_commit):
        raise ValueError("source_commit must be a 40-char git SHA")
    for field in (
        "session_sha256",
        "ledger_snapshot_input_sha256",
        "ledger_manifest_sha256",
        "ledger_manifest_file_sha256",
        "effective_input_file_sha256",
        "run_manifest_file_sha256",
        "state_asof_file_sha256",
    ):
        _require_sha64(raw, field)

    if raw.get("state_asof_valid") is not True:
        raise ValueError("state_asof_valid must be true")
    for field in ("live_quant_run_id", "artifact_id"):
        value = raw.get(field)
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"{field} must be a positive integer")
    if not str(raw.get("artifact_digest", "")).startswith("sha256:"):
        raise ValueError("artifact_digest must be sha256-prefixed")

    source_coverage = raw.get("source_coverage")
    if not isinstance(source_coverage, dict):
        raise ValueError("source_coverage must be an object")
    for family in REQUIRED_SOURCE_FAMILIES:
        status = str(source_coverage.get(family, "")).upper().strip()
        if status not in ALLOWED_SOURCE_STATUS:
            raise ValueError(f"source_coverage {family} must be ATTEMPTED or NOT_APPLICABLE")
    if not str(raw.get("source_coverage_basis", "")).strip():
        raise ValueError("source_coverage_basis is required")

    if "PASS" not in str(raw.get("security_type_status", "")).upper():
        raise ValueError("security_type_status must prove PASS")
    feed_status = str(raw.get("market_feed_status", "")).upper().strip()
    if not feed_status or not any(token in feed_status for token in ("IEX", "SIP", "BOATS", "OVERNIGHT")):
        raise ValueError("market_feed_status must identify a validated Alpaca feed")
    if not str(raw.get("market_feed_validation", "")).strip():
        raise ValueError("market_feed_validation is required")

    candidate_count = int(raw.get("candidate_count", -1))
    eligible_count = int(raw.get("eligible_count", -1))
    ranked_count = int(raw.get("ranked_count", -1))
    coverage = float(raw.get("market_data_coverage_pct", -1))
    if candidate_count < 5:
        raise ValueError("candidate_count must be at least 5")
    if eligible_count < 5 or ranked_count < 5:
        raise ValueError("eligible_count and ranked_count must be at least 5")
    if candidate_count < eligible_count or eligible_count < ranked_count:
        raise ValueError("candidate/eligible/ranked counts are inconsistent")
    if coverage < 80.0:
        raise ValueError("market_data_coverage_pct must be at least 80")
    if raw.get("freeze_ready") is not True:
        raise ValueError("freeze_ready must be true")

    top5 = raw.get("top5")
    top20 = raw.get("top20")
    if not isinstance(top5, list) or len(top5) != 5:
        raise ValueError("top5 must contain exactly five rows")
    if not isinstance(top20, list) or len(top20) < 5:
        raise ValueError("top20 must contain at least five tickers")
    top20_tickers = [str(x).upper().strip() for x in top20]
    if len(top20_tickers) != len(set(top20_tickers)):
        raise ValueError("top20 tickers must be unique")

    seen: set[str] = set()
    ranked_tickers: list[str] = []
    for expected_rank, row in enumerate(top5, start=1):
        if not isinstance(row, dict):
            raise ValueError("each top5 row must be an object")
        if int(row.get("rank", -1)) != expected_rank:
            raise ValueError("top5 ranks must be exactly 1..5")
        ticker = str(row.get("ticker", "")).upper().strip()
        if not TICKER.fullmatch(ticker):
            raise ValueError(f"invalid top5 ticker: {ticker}")
        if ticker in seen:
            raise ValueError("top5 tickers must be unique")
        seen.add(ticker)
        ranked_tickers.append(ticker)
        if not str(row.get("event_id", "")).strip():
            raise ValueError(f"top5 event_id required for {ticker}")
        try:
            float(row.get("quant_score"))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"top5 quant_score required for {ticker}") from exc
    if top20_tickers[:5] != ranked_tickers:
        raise ValueError("top20 first five tickers must match top5 rank order")

    judgment = raw.get("hasol_judgment")
    if not isinstance(judgment, dict) or judgment.get("status") != "VALID_PREOPEN_CHECKPOINT":
        raise ValueError("hasol_judgment.status must be VALID_PREOPEN_CHECKPOINT")
    if not str(judgment.get("reason", "")).strip():
        raise ValueError("hasol_judgment.reason is required")

    if path is not None:
        parent_date = path.parent.name
        if parent_date and parent_date != prediction_date:
            raise ValueError(f"checkpoint path date {parent_date} != prediction_date_et {prediction_date}")

    return {
        "checkpoint_id": checkpoint_id,
        "prediction_date_et": prediction_date,
        "captured_at_utc": captured.isoformat(),
        "regular_open_utc": regular_open.isoformat(),
        "top5": ranked_tickers,
        "candidate_count": candidate_count,
        "eligible_count": eligible_count,
        "coverage": coverage,
        "valid": True,
    }


def validate_path(path: Path) -> list[dict[str, Any]]:
    files = [path] if path.is_file() else sorted(path.rglob("*.json"))
    if not files:
        raise ValueError(f"no checkpoint JSON files found: {path}")
    results = []
    for file in files:
        raw = json.loads(file.read_text(encoding="utf-8"))
        results.append(validate_checkpoint(raw, path=file))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate immutable HASOL pre-open prediction checkpoints")
    parser.add_argument("path", nargs="?", default="runtime/preopen_checkpoints")
    args = parser.parse_args()
    results = validate_path(Path(args.path))
    print(json.dumps({"schema": "HASOL-PREOPEN-CHECKPOINT-VALIDATION-v1", "count": len(results), "valid": True, "checkpoints": results}, indent=2))


if __name__ == "__main__":
    main()
