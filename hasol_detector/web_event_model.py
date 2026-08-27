from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

SCHEMA_VERSION = "HASOL-WEB-CANDIDATES-v2"

ALLOWED_RUN_TYPES = {"PREMARKET", "INTRADAY_EVENT", "E2E_SIM", "SYSTEM_TEST"}
ALLOWED_EVENT_TYPES = {
    "SEC", "IR", "FDA", "EARNINGS", "EARNINGS_NEGATIVE", "GUIDANCE", "CONTRACT",
    "POLICY", "M&A", "FINANCING", "MAJOR_NEWS", "CORPORATE_ACTION", "OTHER_OFFICIAL",
}


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        raise ValueError(f"timestamp must be timezone-aware: {value}")
    return dt


def _is_http_url(value: str | None) -> bool:
    if not value:
        return False
    parsed = urlparse(str(value))
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def event_fingerprint(event: dict[str, Any]) -> str:
    base = "|".join([
        str(event.get("ticker", "")).upper().strip(),
        str(event.get("event_type", "")).upper().strip(),
        str(event.get("official_source_url", "")).strip(),
        str(event.get("event_published_at_utc", "")).strip(),
        str(event.get("headline", "")).strip().lower(),
    ])
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:24]


def _validate_event(event: dict[str, Any], *, production: bool, cutoff: datetime | None) -> dict[str, Any]:
    item = dict(event)
    ticker = str(item.get("ticker", "")).upper().strip()
    if not ticker:
        raise ValueError("candidate ticker is required")
    item["ticker"] = ticker

    event_type = str(item.get("event_type", "")).upper().strip()
    if event_type not in ALLOWED_EVENT_TYPES:
        raise ValueError(f"unsupported event_type for {ticker}: {event_type}")
    item["event_type"] = event_type

    published = _parse_dt(item.get("event_published_at_utc"))
    if production and published is None:
        raise ValueError(f"event_published_at_utc required for production candidate {ticker}")
    if cutoff is not None and published is not None and published > cutoff:
        raise ValueError(f"future leakage: {ticker} event published after cutoff")

    official_url = item.get("official_source_url")
    official_verified = bool(item.get("official_verified", False))
    if production:
        if not _is_http_url(official_url):
            raise ValueError(f"official_source_url required for production candidate {ticker}")
        if not official_verified:
            raise ValueError(f"official source must be verified for production candidate {ticker}")

    item["event_id"] = str(item.get("event_id") or event_fingerprint(item))
    item["event_fingerprint"] = str(item.get("event_fingerprint") or event_fingerprint(item))
    item["axis"] = str(item.get("axis", "UNKNOWN")).upper().strip() or "UNKNOWN"
    item["official_verified"] = official_verified
    item["official_source_url"] = str(official_url or "")
    item["headline"] = str(item.get("headline", "")).strip()
    item["flow_path"] = str(item.get("flow_path", "")).strip()
    return item


def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
    run_type = str(payload.get("run_type", "")).upper().strip()
    if run_type not in ALLOWED_RUN_TYPES:
        raise ValueError(f"run_type must be one of {sorted(ALLOWED_RUN_TYPES)}")
    production = bool(payload.get("eligible_for_prediction", False))
    cutoff = _parse_dt(payload.get("cutoff_et"))
    if production and cutoff is None:
        raise ValueError("cutoff_et is required when eligible_for_prediction=true")

    raw = payload.get("candidates")
    if not isinstance(raw, list):
        raise ValueError("candidates must be a list")

    seen: set[str] = set()
    verified_events: list[dict[str, Any]] = []
    for event in raw:
        if not isinstance(event, dict):
            raise ValueError("each candidate event must be an object")
        item = _validate_event(event, production=production, cutoff=cutoff)
        fp = item["event_fingerprint"]
        if fp in seen:
            continue
        seen.add(fp)
        verified_events.append(item)

    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in verified_events:
        grouped.setdefault(item["ticker"], []).append(item)

    candidates: list[dict[str, Any]] = []
    for ticker in sorted(grouped):
        events = sorted(grouped[ticker], key=lambda x: (x.get("event_published_at_utc", ""), x["event_id"]))
        latest = events[-1]
        candidates.append({
            "ticker": ticker,
            "event_count": len(events),
            "event_ids": ";".join(e["event_id"] for e in events),
            "event_types": ";".join(sorted({e["event_type"] for e in events})),
            "axes": ";".join(sorted({e["axis"] for e in events})),
            "event_id": latest["event_id"],
            "event_type": latest["event_type"],
            "axis": latest["axis"],
            "event_published_at_utc": latest.get("event_published_at_utc", ""),
            "official_source_url": latest.get("official_source_url", ""),
            "official_verified": all(bool(e.get("official_verified")) for e in events) if production else bool(latest.get("official_verified")),
            "headline": latest.get("headline", ""),
            "flow_path": latest.get("flow_path", ""),
            "event_bundle": json.dumps(events, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        })

    out = dict(payload)
    out["run_type"] = run_type
    out["normalized_at_utc"] = datetime.now(ZoneInfo("UTC")).isoformat()
    out["event_count_raw"] = len(raw)
    out["event_count_deduped"] = len(verified_events)
    out["candidate_count"] = len(candidates)
    out["candidates"] = candidates
    return out
