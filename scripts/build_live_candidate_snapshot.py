from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hasol_detector.web_event_model import SCHEMA_VERSION, normalize_payload

SESSION_SCHEMA = "HASOL-WEB-SESSION-v1"
EVENT_SCHEMA = "HASOL-WEB-EVENT-v1"
DECISION_SCHEMA = "HASOL-WEB-DECISION-v1"
LEDGER_MANIFEST_SCHEMA = "HASOL-WEB-LEDGER-MANIFEST-v1"
MATERIALITY_DROP = "MATERIALITY_DROP"
MATERIALITY_KEEP = "MATERIALITY_KEEP"
ALLOWED_DECISIONS = {MATERIALITY_DROP, MATERIALITY_KEEP}
RUN_TYPE_ALIASES = {
    "PREMARKET": "PREMARKET",
    "INTRADAY_EVENT": "INTRADAY_EVENT",
    "INTRADAY": "INTRADAY_EVENT",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"JSON object required: {path}")
    return raw


def _parse_aware_dt(value: str, *, field: str, path: Path) -> datetime:
    text = str(value).strip().replace("Z", "+00:00")
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


def _json_files(root: Path, prediction_date_et: str) -> list[Path]:
    target = root / prediction_date_et
    if not target.exists():
        return []
    return sorted(path for path in target.rglob("*.json") if path.is_file())


def _event_files(root: Path, prediction_date_et: str) -> list[Path]:
    return _json_files(root, prediction_date_et)


def _decision_files(root: Path | None, prediction_date_et: str) -> list[Path]:
    if root is None:
        return []
    return _json_files(root, prediction_date_et)


def _load_event(path: Path, *, prediction_date_et: str, run_type: str) -> dict[str, Any]:
    raw = _read_json(path)
    if raw.get("ledger_schema") == EVENT_SCHEMA or "event" in raw:
        target_date = str(raw.get("prediction_date_et", "")).strip()
        if target_date != prediction_date_et:
            raise ValueError(f"event ledger target date mismatch in {path}: {target_date}")
        target_run_type = _canonical_run_type(raw.get("run_type", run_type), field="event run_type", path=path)
        if target_run_type != run_type:
            raise ValueError(f"event ledger run_type mismatch in {path}: {target_run_type}")
        event = raw.get("event")
        if not isinstance(event, dict):
            raise ValueError(f"event object required in {path}")
        return dict(event)
    return raw


def _load_decision(path: Path, *, prediction_date_et: str, run_type: str) -> dict[str, Any]:
    raw = _read_json(path)
    if raw.get("decision_schema") != DECISION_SCHEMA:
        raise ValueError(f"decision_schema must be {DECISION_SCHEMA} in {path}")
    decision_id = str(raw.get("decision_id", "")).strip()
    if not decision_id:
        raise ValueError(f"decision_id is required in {path}")
    target_date = str(raw.get("prediction_date_et", "")).strip()
    if target_date != prediction_date_et:
        raise ValueError(f"decision target date mismatch in {path}: {target_date}")
    target_run_type = _canonical_run_type(raw.get("run_type", run_type), field="decision run_type", path=path)
    if target_run_type != run_type:
        raise ValueError(f"decision run_type mismatch in {path}: {target_run_type}")
    event_id = str(raw.get("event_id", "")).strip()
    if not event_id:
        raise ValueError(f"decision event_id is required in {path}")
    action = str(raw.get("action", "")).upper().strip()
    if action not in ALLOWED_DECISIONS:
        raise ValueError(f"unsupported materiality decision in {path}: {action}")
    decided_at = _parse_aware_dt(str(raw.get("decided_at_utc", "")), field="decided_at_utc", path=path)
    if action == MATERIALITY_DROP and not str(raw.get("reason", "")).strip():
        raise ValueError(f"MATERIALITY_DROP reason is required in {path}")
    out = dict(raw)
    out["decision_id"] = decision_id
    out["event_id"] = event_id
    out["action"] = action
    out["run_type"] = target_run_type
    out["decided_at_utc"] = decided_at.isoformat().replace("+00:00", "Z")
    out["_decided_at_sort"] = decided_at.timestamp()
    return out


def build_snapshot(
    session_path: Path,
    premarket_root: Path,
    intraday_root: Path,
    output_path: Path,
    manifest_path: Path,
    decision_root: Path | None = None,
) -> dict[str, Any]:
    session = _read_json(session_path)
    if session.get("session_schema") != SESSION_SCHEMA:
        raise ValueError(f"session_schema must be {SESSION_SCHEMA}")

    prediction_date_et = str(session.get("prediction_date_et", "")).strip()
    if not prediction_date_et:
        raise ValueError("prediction_date_et is required")

    raw_run_type = str(session.get("run_type", "")).upper().strip()
    run_type = _canonical_run_type(raw_run_type, field="session run_type", path=session_path)
    root = premarket_root if run_type == "PREMARKET" else intraday_root

    prediction_eligible = bool(session.get("eligible_for_prediction", False))
    session_as_of = _parse_aware_dt(str(session.get("as_of_utc", "")), field="as_of_utc", path=session_path)
    cutoff_utc: datetime | None = None
    if run_type == "PREMARKET" and prediction_eligible:
        cutoff_utc = _parse_aware_dt(str(session.get("cutoff_et", "")), field="cutoff_et", path=session_path)

    event_paths = _event_files(root, prediction_date_et)
    loaded: list[tuple[Path, dict[str, Any]]] = [
        (path, _load_event(path, prediction_date_et=prediction_date_et, run_type=run_type))
        for path in event_paths
    ]
    if run_type == "PREMARKET" and prediction_eligible:
        for path, event in loaded:
            published_at = _parse_aware_dt(
                str(event.get("event_published_at_utc", "")), field="event_published_at_utc", path=path
            )
            if published_at > session_as_of:
                raise ValueError(
                    "event publication is newer than session as_of_utc: "
                    f"event_id={event.get('event_id')} published={published_at.isoformat()} session={session_as_of.isoformat()}"
                )
            if cutoff_utc is not None and published_at > cutoff_utc:
                raise ValueError(
                    "premarket event publication is after prediction information barrier: "
                    f"event_id={event.get('event_id')} published={published_at.isoformat()} cutoff={cutoff_utc.isoformat()}"
                )

    loaded.sort(
        key=lambda pair: (
            str(pair[1].get("event_published_at_utc", "")),
            str(pair[1].get("ticker", "")).upper(),
            str(pair[1].get("event_id", "")),
            pair[0].as_posix(),
        )
    )
    loaded_event_ids = {
        str(event.get("event_id", "")).strip()
        for _, event in loaded
        if str(event.get("event_id", "")).strip()
    }

    decision_paths = _decision_files(decision_root, prediction_date_et)
    decisions: list[tuple[Path, dict[str, Any]]] = [
        (path, _load_decision(path, prediction_date_et=prediction_date_et, run_type=run_type))
        for path in decision_paths
    ]
    seen_decision_ids: set[str] = set()
    for path, decision in decisions:
        decision_id = str(decision["decision_id"])
        if decision_id in seen_decision_ids:
            raise ValueError(f"duplicate decision_id in materiality ledger: {decision_id}")
        seen_decision_ids.add(decision_id)
        if str(decision["event_id"]) not in loaded_event_ids:
            raise ValueError(f"materiality decision references unknown event_id in {path}: {decision['event_id']}")

    decisions.sort(
        key=lambda pair: (
            float(pair[1]["_decided_at_sort"]),
            str(pair[1]["decision_id"]),
            pair[0].as_posix(),
        )
    )

    applicable_decisions: list[tuple[Path, dict[str, Any]]] = []
    ignored_post_cutoff_decision_ids: list[str] = []
    for path, decision in decisions:
        decided_at_utc = datetime.fromtimestamp(float(decision["_decided_at_sort"]), tz=timezone.utc)
        applies = cutoff_utc is None or decided_at_utc <= cutoff_utc
        decision["_applies_to_snapshot"] = applies
        if applies:
            applicable_decisions.append((path, decision))
        else:
            ignored_post_cutoff_decision_ids.append(str(decision["decision_id"]))

    latest_decision_by_event: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path, decision in applicable_decisions:
        latest_decision_by_event[str(decision["event_id"])] = (path, decision)

    excluded_event_ids = {
        event_id
        for event_id, (_, decision) in latest_decision_by_event.items()
        if str(decision["action"]) == MATERIALITY_DROP
    }
    active_loaded = [
        (path, event)
        for path, event in loaded
        if str(event.get("event_id", "")).strip() not in excluded_event_ids
    ]
    events = [event for _, event in active_loaded]

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "run_type": run_type,
        "eligible_for_prediction": prediction_eligible,
        "prediction_date_et": prediction_date_et,
        "as_of_utc": session.get("as_of_utc"),
        "cutoff_et": session.get("cutoff_et"),
        "candidates": events,
    }
    for key in (
        "rollover_from_prediction_date_et",
        "rollover_policy",
        "stage_marker",
        "source_recall_policy",
        "notes",
    ):
        if key in session:
            payload[key] = session[key]

    normalized = normalize_payload(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    file_rows = []
    for path, event in loaded:
        file_rows.append(
            {
                "path": path.as_posix(),
                "sha256": _sha256_bytes(path.read_bytes()),
                "event_id": str(event.get("event_id", "")),
                "ticker": str(event.get("ticker", "")).upper(),
                "active": str(event.get("event_id", "")).strip() not in excluded_event_ids,
            }
        )

    decision_rows = []
    for path, decision in decisions:
        applies = bool(decision.get("_applies_to_snapshot", False))
        decision_rows.append(
            {
                "path": path.as_posix(),
                "sha256": _sha256_bytes(path.read_bytes()),
                "decision_id": str(decision["decision_id"]),
                "event_id": str(decision["event_id"]),
                "action": str(decision["action"]),
                "decided_at_utc": str(decision["decided_at_utc"]),
                "applies_to_snapshot": applies,
                "ignored_reason": None if applies else "AFTER_PREDICTION_CUTOFF",
            }
        )

    latest_decisions = []
    for event_id in sorted(latest_decision_by_event):
        path, decision = latest_decision_by_event[event_id]
        latest_decisions.append(
            {
                "event_id": event_id,
                "action": str(decision["action"]),
                "reason": str(decision.get("reason", "")),
                "decided_at_utc": str(decision["decided_at_utc"]),
                "decision_id": str(decision["decision_id"]),
                "path": path.as_posix(),
            }
        )

    ledger_manifest = {
        "schema_version": LEDGER_MANIFEST_SCHEMA,
        "session_schema": SESSION_SCHEMA,
        "session_path": session_path.as_posix(),
        "session_sha256": _sha256_json(session),
        "prediction_date_et": prediction_date_et,
        "run_type": run_type,
        "run_type_input": raw_run_type,
        "run_type_canonicalized": raw_run_type != run_type,
        "eligible_for_prediction": prediction_eligible,
        "event_root": (root / prediction_date_et).as_posix(),
        "event_file_count": len(event_paths),
        "active_event_file_count": len(active_loaded),
        "decision_root": (decision_root / prediction_date_et).as_posix() if decision_root is not None else None,
        "decision_file_count": len(decision_paths),
        "applicable_decision_count": len(applicable_decisions),
        "ignored_post_cutoff_decision_ids": sorted(ignored_post_cutoff_decision_ids),
        "excluded_event_ids": sorted(excluded_event_ids),
        "event_count_raw": int(normalized.get("event_count_raw", 0)),
        "event_count_deduped": int(normalized.get("event_count_deduped", 0)),
        "candidate_count": int(normalized.get("candidate_count", 0)),
        "snapshot_input_sha256": _sha256_json(payload),
        "event_files": file_rows,
        "decision_files": decision_rows,
        "latest_materiality_decisions": latest_decisions,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(ledger_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ledger_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build deterministic HASOL live snapshot from append-only event and materiality-decision ledgers")
    parser.add_argument("--session", default="runtime/web_candidates/session.json")
    parser.add_argument("--premarket-root", default="runtime/web_candidates/events")
    parser.add_argument("--intraday-root", default="runtime/web_candidates/intraday")
    parser.add_argument("--decision-root", default="runtime/web_candidates/decisions")
    parser.add_argument("--output", default="output_live_quant/effective_input.json")
    parser.add_argument("--manifest", default="output_live_quant/ledger_manifest.json")
    args = parser.parse_args()
    manifest = build_snapshot(
        Path(args.session),
        Path(args.premarket_root),
        Path(args.intraday_root),
        Path(args.output),
        Path(args.manifest),
        Path(args.decision_root),
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
