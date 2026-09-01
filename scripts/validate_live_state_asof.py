from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SESSION_SCHEMA = "HASOL-WEB-SESSION-v1"
DECISION_SCHEMA = "HASOL-WEB-DECISION-v1"
EVENT_SCHEMA = "HASOL-WEB-EVENT-v1"
RUN_TYPE_ALIASES = {
    "PREMARKET": "PREMARKET",
    "INTRADAY_EVENT": "INTRADAY_EVENT",
    "INTRADAY": "INTRADAY_EVENT",
}


def _read_json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"JSON object required: {path}")
    return raw


def _parse_aware(value: object, *, field: str, path: Path) -> datetime:
    text = str(value or "").strip().replace("Z", "+00:00")
    if not text:
        raise ValueError(f"{field} is required in {path}")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"invalid {field} in {path}: {value}") from exc
    if dt.tzinfo is None:
        raise ValueError(f"{field} must be timezone-aware in {path}")
    return dt.astimezone(timezone.utc)


def _canonical_run_type(value: object, *, field: str, path: Path) -> str:
    raw = str(value or "").upper().strip()
    canonical = RUN_TYPE_ALIASES.get(raw)
    if canonical is None:
        raise ValueError(f"unsupported {field} in {path}: {raw}")
    return canonical


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _files(root: Path | None, prediction_date_et: str) -> list[Path]:
    if root is None:
        return []
    target = root / prediction_date_et
    if not target.exists():
        return []
    return sorted(path for path in target.rglob("*.json") if path.is_file())


def validate_state_asof(
    session_path: Path,
    effective_input_path: Path,
    premarket_root: Path,
    intraday_root: Path,
    decision_root: Path | None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    session = _read_json(session_path)
    if session.get("session_schema") != SESSION_SCHEMA:
        raise ValueError(f"session_schema must be {SESSION_SCHEMA}")

    prediction_date_et = str(session.get("prediction_date_et", "")).strip()
    if not prediction_date_et:
        raise ValueError("prediction_date_et is required")
    raw_run_type = str(session.get("run_type", "")).upper().strip()
    run_type = _canonical_run_type(raw_run_type, field="session run_type", path=session_path)

    session_as_of = _parse_aware(session.get("as_of_utc"), field="as_of_utc", path=session_path)
    cutoff: datetime | None = None
    if run_type == "PREMARKET" and bool(session.get("eligible_for_prediction", False)):
        cutoff = _parse_aware(session.get("cutoff_et"), field="cutoff_et", path=session_path)

    effective = _read_json(effective_input_path)
    effective_run_type = _canonical_run_type(effective.get("run_type", run_type), field="effective run_type", path=effective_input_path)
    if effective_run_type != run_type:
        raise ValueError(f"effective input run_type does not match session: effective={effective_run_type} session={run_type}")
    effective_as_of = _parse_aware(effective.get("as_of_utc"), field="as_of_utc", path=effective_input_path)
    if effective_as_of != session_as_of:
        raise ValueError(
            f"effective input as_of_utc does not match session: effective={_iso(effective_as_of)} session={_iso(session_as_of)}"
        )

    decision_files = _files(decision_root, prediction_date_et)
    applicable_decisions: list[tuple[str, datetime]] = []
    ignored_post_cutoff: list[str] = []
    for path in decision_files:
        raw = _read_json(path)
        if raw.get("decision_schema") != DECISION_SCHEMA:
            raise ValueError(f"decision_schema must be {DECISION_SCHEMA} in {path}")
        decision_run_type = _canonical_run_type(raw.get("run_type", run_type), field="decision run_type", path=path)
        if decision_run_type != run_type:
            raise ValueError(f"decision run_type mismatch in {path}: {decision_run_type}")
        decision_id = str(raw.get("decision_id", "")).strip()
        decided_at = _parse_aware(raw.get("decided_at_utc"), field="decided_at_utc", path=path)
        applies = cutoff is None or decided_at <= cutoff
        if applies:
            if decided_at > session_as_of:
                raise ValueError(
                    "session as_of_utc predates an applicable materiality decision: "
                    f"session={_iso(session_as_of)} latest_decision={_iso(decided_at)}"
                )
            applicable_decisions.append((decision_id, decided_at))
        else:
            ignored_post_cutoff.append(decision_id)

    max_decision = max((dt for _, dt in applicable_decisions), default=None)

    event_root = premarket_root if run_type == "PREMARKET" else intraday_root
    event_files = _files(event_root, prediction_date_et)
    recorded_events: list[tuple[str, datetime]] = []
    published_events: list[tuple[str, datetime]] = []
    late_recorded_event_ids: list[str] = []
    for path in event_files:
        raw = _read_json(path)
        if raw.get("ledger_schema") == EVENT_SCHEMA or "event" in raw:
            event_run_type = _canonical_run_type(raw.get("run_type", run_type), field="event run_type", path=path)
            if event_run_type != run_type:
                raise ValueError(f"event run_type mismatch in {path}: {event_run_type}")
        event = raw.get("event") if raw.get("ledger_schema") == EVENT_SCHEMA or "event" in raw else raw
        if not isinstance(event, dict):
            raise ValueError(f"event object required in {path}")
        event_id = str(event.get("event_id", "")).strip()

        published_value = event.get("event_published_at_utc")
        if published_value:
            published_at = _parse_aware(published_value, field="event_published_at_utc", path=path)
            published_events.append((event_id, published_at))
            if published_at > session_as_of:
                raise ValueError(
                    "session as_of_utc predates event publication: "
                    f"event_id={event_id} published={_iso(published_at)} session={_iso(session_as_of)}"
                )
            if cutoff is not None and published_at > cutoff:
                raise ValueError(
                    "premarket event publication is after prediction information barrier: "
                    f"event_id={event_id} published={_iso(published_at)} cutoff={_iso(cutoff)}"
                )

        lineage = event.get("lineage") if isinstance(event.get("lineage"), dict) else {}
        recorded_value = raw.get("recorded_at_utc") or lineage.get("discovered_at_utc")
        if recorded_value:
            recorded_at = _parse_aware(recorded_value, field="recorded_at_utc/discovered_at_utc", path=path)
            recorded_events.append((event_id, recorded_at))
            if recorded_at > session_as_of:
                raise ValueError(
                    "session as_of_utc predates recorded event state: "
                    f"event_id={event_id} recorded={_iso(recorded_at)} session={_iso(session_as_of)}"
                )
            if cutoff is not None and recorded_at > cutoff:
                late_recorded_event_ids.append(event_id)

    max_event_recorded = max((dt for _, dt in recorded_events), default=None)
    max_event_published = max((dt for _, dt in published_events), default=None)
    report = {
        "schema": "HASOL-LIVE-STATE-ASOF-v2",
        "valid": True,
        "prediction_date_et": prediction_date_et,
        "run_type": run_type,
        "run_type_input": raw_run_type,
        "run_type_canonicalized": raw_run_type != run_type,
        "session_as_of_utc": _iso(session_as_of),
        "effective_input_as_of_utc": _iso(effective_as_of),
        "cutoff_utc": _iso(cutoff),
        "decision_file_count": len(decision_files),
        "applicable_decision_count": len(applicable_decisions),
        "ignored_post_cutoff_decision_ids": sorted(ignored_post_cutoff),
        "max_applicable_decision_at_utc": _iso(max_decision),
        "event_file_count": len(event_files),
        "published_event_count": len(published_events),
        "max_published_event_at_utc": _iso(max_event_published),
        "recorded_event_count": len(recorded_events),
        "max_recorded_event_at_utc": _iso(max_event_recorded),
        "late_recorded_event_ids": sorted(set(late_recorded_event_ids)),
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate HASOL session as-of metadata against effective ledger state")
    parser.add_argument("--session", default="runtime/web_candidates/session.json")
    parser.add_argument("--effective-input", default="output_live_quant/effective_input.json")
    parser.add_argument("--premarket-root", default="runtime/web_candidates/events")
    parser.add_argument("--intraday-root", default="runtime/web_candidates/intraday")
    parser.add_argument("--decision-root", default="runtime/web_candidates/decisions")
    parser.add_argument("--output", default="output_live_quant/state_asof_validation.json")
    args = parser.parse_args()
    report = validate_state_asof(
        Path(args.session),
        Path(args.effective_input),
        Path(args.premarket_root),
        Path(args.intraday_root),
        Path(args.decision_root),
        Path(args.output),
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
