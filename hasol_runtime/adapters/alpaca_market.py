from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from statistics import mean
from typing import Any
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
ALLOWED_EXCHANGE_MAP = {
    "NASDAQ": "NASDAQ",
    "NYSE": "NYSE",
    "AMEX": "NYSE_AMERICAN",
    "NYSE_AMERICAN": "NYSE_AMERICAN",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _finite(value: Any, *, field: str, ticker: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{ticker}: {field} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{ticker}: {field} must be finite")
    return number


def _parse_ts(value: Any, *, ticker: str) -> datetime:
    if not value:
        raise ValueError(f"{ticker}: bar timestamp missing")
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{ticker}: invalid bar timestamp {value!r}") from exc
    if dt.utcoffset() is None:
        raise ValueError(f"{ticker}: bar timestamp must include offset")
    return dt


def _normalize_assets(assets: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Normalize a pre-classified security-master export.

    Deliberately fail-closed: Alpaca `us_equity` alone is not treated as proof that a
    symbol is a common stock. `security_type=COMMON_STOCK` must come from a separate,
    explicit classification step/source.
    """
    out: dict[str, dict[str, Any]] = {}
    for raw in assets:
        ticker = str(raw.get("symbol") or raw.get("ticker") or "").strip().upper()
        if not ticker:
            raise ValueError("asset missing symbol/ticker")
        if ticker in out:
            raise ValueError(f"duplicate asset ticker: {ticker}")

        status = str(raw.get("status", "active")).lower()
        asset_class = str(raw.get("class") or raw.get("asset_class") or "us_equity").lower()
        exchange_raw = str(raw.get("exchange") or "").upper().strip()
        exchange = ALLOWED_EXCHANGE_MAP.get(exchange_raw)
        security_type = raw.get("security_type")
        classification_source = raw.get("classification_source")

        if status != "active" or asset_class != "us_equity" or exchange is None:
            continue
        if security_type != "COMMON_STOCK":
            continue
        if not classification_source:
            raise ValueError(f"{ticker}: COMMON_STOCK classification_source missing")
        if bool(raw.get("excluded_security_flag", False)):
            continue

        out[ticker] = {
            "ticker": ticker,
            "exchange": exchange,
            "security_type": "COMMON_STOCK",
            "excluded_security_flag": False,
            "classification_source": str(classification_source),
            "asset_status": status,
            "asset_class": asset_class,
        }
    if not out:
        raise ValueError("classified asset universe is empty")
    return out


def _extract_bars_payload(bars_payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    # Accept native Alpaca connector response (`bars`) or a direct symbol->bars map.
    candidate = bars_payload.get("bars") if isinstance(bars_payload, dict) else None
    if candidate is None and isinstance(bars_payload, dict):
        candidate = bars_payload
    if not isinstance(candidate, dict):
        raise ValueError("bars payload must contain a symbol->bars mapping")
    return candidate


def build_market_snapshot(
    *,
    assets: list[dict[str, Any]],
    bars_payload: dict[str, Any],
    cutoff_et: str,
    source_ref: str,
    feed: str,
) -> dict[str, Any]:
    """Build deterministic market fields for the official v3 universe.

    Contract:
    - cutoff is explicit 16:00 ET with offset;
    - cutoff-session close is used as the current regular close;
    - ADV20 uses the *20 completed sessions before the cutoff session* and therefore
      excludes cutoff-day dollar volume;
    - no synthetic fills/fallbacks;
    - future bars and duplicate session bars are rejected;
    - insufficient histories are marked ineligible, not fabricated.
    """
    try:
        cutoff = datetime.fromisoformat(cutoff_et)
    except ValueError as exc:
        raise ValueError("cutoff_et must be ISO8601") from exc
    if cutoff.utcoffset() is None:
        raise ValueError("cutoff_et must include offset")
    cutoff_local = cutoff.astimezone(ET)
    if (cutoff_local.hour, cutoff_local.minute, cutoff_local.second) != (16, 0, 0):
        raise ValueError("cutoff_et must resolve to 16:00:00 America/New_York")
    if not source_ref:
        raise ValueError("source_ref is required")
    if feed not in {"sip", "delayed_sip", "iex"}:
        raise ValueError("feed must be sip, delayed_sip, or iex")

    classified = _normalize_assets(assets)
    bars_by_symbol = _extract_bars_payload(bars_payload)
    cutoff_session = cutoff_local.date()

    rows: list[dict[str, Any]] = []
    missing_bars: list[str] = []
    insufficient_history: list[str] = []

    for ticker in sorted(classified):
        raw_bars = bars_by_symbol.get(ticker)
        if not isinstance(raw_bars, list) or not raw_bars:
            missing_bars.append(ticker)
            continue

        sessions: dict[str, dict[str, Any]] = {}
        for raw in raw_bars:
            ts = _parse_ts(raw.get("timestamp"), ticker=ticker)
            if ts > cutoff:
                raise ValueError(f"{ticker}: future bar after cutoff: {ts.isoformat()}")
            session_date = ts.astimezone(ET).date()
            if session_date > cutoff_session:
                raise ValueError(f"{ticker}: future trading session after cutoff: {session_date}")
            key = session_date.isoformat()
            if key in sessions:
                raise ValueError(f"{ticker}: duplicate daily bar for session {key}")

            close = _finite(raw.get("close"), field="close", ticker=ticker)
            volume = _finite(raw.get("volume"), field="volume", ticker=ticker)
            if close <= 0 or volume < 0:
                raise ValueError(f"{ticker}: invalid close/volume in session {key}")
            sessions[key] = {
                "timestamp": ts.isoformat(),
                "session": key,
                "close": close,
                "volume": volume,
            }

        cutoff_key = cutoff_session.isoformat()
        cutoff_bar = sessions.get(cutoff_key)
        if cutoff_bar is None:
            missing_bars.append(ticker)
            continue

        prior = [bar for key, bar in sorted(sessions.items()) if key < cutoff_key]
        if len(prior) < 20:
            insufficient_history.append(ticker)
            continue
        prior20 = prior[-20:]
        adv20 = mean(bar["close"] * bar["volume"] for bar in prior20)

        base = classified[ticker]
        rows.append({
            **base,
            "close": round(cutoff_bar["close"], 8),
            "adv20_usd": round(adv20, 8),
            "completed_sessions": len(prior),
            "price_source": source_ref,
            "market_data_feed": feed,
            "cutoff_session": cutoff_key,
            "adv20_sessions": [bar["session"] for bar in prior20],
            "adv20_excludes_cutoff_session": True,
            "market_lineage": {
                "provider": "ALPACA",
                "feed": feed,
                "source_ref": source_ref,
                "cutoff_et": cutoff.isoformat(),
            },
        })

    rows.sort(key=lambda row: row["ticker"])
    observed = len(rows)
    expected = len(classified)
    coverage = observed / expected if expected else 0.0

    frozen_core = {
        "schema": "HASOL-ALPACA-MARKET-SNAPSHOT-v1",
        "cutoff_et": cutoff.isoformat(),
        "feed": feed,
        "source_ref": source_ref,
        "classified_asset_count": expected,
        "observed_count": observed,
        "missing_bars": sorted(missing_bars),
        "insufficient_history": sorted(insufficient_history),
        "rows": rows,
    }
    return {
        **frozen_core,
        "coverage": round(coverage, 10),
        "snapshot_hash": _sha256(frozen_core),
    }
