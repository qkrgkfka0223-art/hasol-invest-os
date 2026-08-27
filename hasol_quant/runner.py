from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")


def completed_session_end_utc(now_utc: datetime) -> datetime:
    """Return an end timestamp that never includes an in-progress US regular session."""
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    now_et = now_utc.astimezone(NY)
    if now_et.timetz().replace(tzinfo=None) < time(16, 20):
        start_today_et = datetime.combine(now_et.date(), time(0, 0), tzinfo=NY)
        return (start_today_et - timedelta(microseconds=1)).astimezone(timezone.utc)
    return now_utc.astimezone(timezone.utc)


def run_full_market_quant(output_dir: Path, feed: str = "sip", lookback_calendar_days: int = 120, end_utc: datetime | None = None) -> dict:
    """Deprecated compatibility entry point.

    GitHub no longer authenticates to Alpaca or scans the full US market. Production detection is
    Web-event-first and runs through scripts.run_web_candidate_quant. Final market validation is
    performed by the connected Alpaca app after the candidate set is reduced.
    """
    raise RuntimeError(
        "DEPRECATED_FULL_MARKET_ALPACA_PATH: use scripts.run_web_candidate_quant; "
        "GitHub must not require Alpaca API credentials."
    )
