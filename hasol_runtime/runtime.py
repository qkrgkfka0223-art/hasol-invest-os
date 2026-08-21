from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import asdict
from datetime import datetime
from typing import Any

from .contracts import CONTRACT, RunOutcome, RuntimeState
from .scoring import rank_top20, rank_top5


class HasolRuntime:
    """Fail-closed deterministic HASOL model loop.

    This runtime never converts missing/broken upstream data into "no candidate".
    Official output is emitted only when all mandatory gates pass.
    """

    def __init__(self, payload: dict[str, Any]):
        self.payload = copy.deepcopy(payload)
        self.state = RuntimeState.BOOT
        self.errors: list[str] = []
        self.audit: list[dict[str, Any]] = []
        self.universe_hash: str | None = None
        self.prediction_hash: str | None = None

    @staticmethod
    def _canonical(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)

    @classmethod
    def _sha256(cls, value: Any) -> str:
        return hashlib.sha256(cls._canonical(value).encode("utf-8")).hexdigest()

    @classmethod
    def recompute_prediction_hash(cls, prediction: dict[str, Any]) -> str:
        frozen = copy.deepcopy(prediction)
        frozen.pop("prediction_hash", None)
        return cls._sha256(frozen)

    def _transition(self, state: RuntimeState, detail: str = "PASS") -> None:
        self.state = state
        self.audit.append({"state": state.value, "detail": detail})

    def _invalidate(self, outcome: RunOutcome, message: str) -> dict[str, Any]:
        self.errors.append(message)
        self._transition(RuntimeState.INVALID, message)
        return {
            "outcome": outcome.value,
            "state": self.state.value,
            "official_prediction": False,
            "errors": self.errors,
            "audit": self.audit,
        }

    def _validate_run_metadata(self) -> None:
        meta = self.payload.get("run", {})
        required = ("run_id", "cutoff_et", "strategy_version", "ruleset_version", "snapshot_ref")
        missing = [k for k in required if not meta.get(k)]
        if missing:
            raise ValueError(f"run metadata missing: {missing}")
        if meta["strategy_version"] != CONTRACT.strategy_version:
            raise ValueError("strategy_version mismatch")
        if meta["ruleset_version"] != CONTRACT.ruleset_version:
            raise ValueError("ruleset_version mismatch")
        cutoff = str(meta["cutoff_et"])
        if "T16:00:00" not in cutoff:
            raise ValueError("cutoff_et must be explicit 16:00:00 America/New_York close with offset")
        try:
            parsed = datetime.fromisoformat(cutoff)
        except ValueError as exc:
            raise ValueError("cutoff_et must be ISO8601 with offset") from exc
        if parsed.utcoffset() is None:
            raise ValueError("cutoff_et must include UTC offset")

    @staticmethod
    def _is_common_stock(row: dict[str, Any]) -> bool:
        return row.get("security_type") == "COMMON_STOCK" and not bool(row.get("excluded_security_flag", False))

    def _eligible_universe(self) -> list[dict[str, Any]]:
        raw = self.payload.get("universe", [])
        if not isinstance(raw, list) or not raw:
            raise ValueError("universe is empty")

        seen: set[str] = set()
        eligible: list[dict[str, Any]] = []
        for row in raw:
            ticker = str(row.get("ticker", "")).strip().upper()
            if not ticker:
                raise ValueError("universe row missing ticker")
            if ticker in seen:
                raise ValueError(f"duplicate ticker: {ticker}")
            seen.add(ticker)
            row["ticker"] = ticker

            mandatory = ("exchange", "security_type", "close", "adv20_usd", "completed_sessions", "engine_raw")
            missing = [k for k in mandatory if row.get(k) is None]
            if missing:
                raise ValueError(f"{ticker}: mandatory universe fields missing: {missing}")

            if row["exchange"] not in CONTRACT.allowed_exchanges:
                continue
            if not self._is_common_stock(row):
                continue
            if float(row["close"]) < CONTRACT.min_price:
                continue
            if float(row["adv20_usd"]) < CONTRACT.min_adv20_usd:
                continue
            if int(row["completed_sessions"]) < CONTRACT.min_completed_sessions:
                continue
            eligible.append(row)

        eligible.sort(key=lambda r: r["ticker"])
        if len(eligible) < CONTRACT.top20_count:
            raise ValueError(f"eligible universe too small: {len(eligible)}")
        return eligible

    def _validate_coverage(self, eligible: list[dict[str, Any]]) -> None:
        meta = self.payload.get("coverage", {})
        expected = meta.get("eligible_expected")
        observed = meta.get("market_data_observed")
        if expected is None or observed is None:
            raise ValueError("coverage eligible_expected and market_data_observed are mandatory")
        expected = int(expected)
        observed = int(observed)
        if expected <= 0 or observed < 0 or observed > expected:
            raise ValueError("coverage counts invalid")
        coverage = observed / expected
        if coverage < CONTRACT.required_market_coverage:
            raise ValueError(f"market coverage {coverage:.4f} < {CONTRACT.required_market_coverage:.2f}")
        if expected != len(eligible):
            raise ValueError(
                f"eligible_expected={expected} but deterministic eligible universe={len(eligible)}; "
                "exact universe classification is not reconciled"
            )

    @staticmethod
    def _validate_evidence(row: dict[str, Any], cutoff_et: str) -> None:
        if not row.get("price_source"):
            raise ValueError(f"{row['ticker']}: price_source missing")
        if not row.get("invalidation"):
            raise ValueError(f"{row['ticker']}: invalidation missing")
        if not row.get("thesis"):
            raise ValueError(f"{row['ticker']}: thesis missing")
        if not row.get("counter_thesis"):
            raise ValueError(f"{row['ticker']}: counter_thesis missing")
        evidence = row.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError(f"{row['ticker']}: evidence bundle empty")
        cutoff = datetime.fromisoformat(cutoff_et)
        for item in evidence:
            for key in ("type", "published_at_utc", "ref", "claim", "freshness"):
                if not item.get(key):
                    raise ValueError(f"{row['ticker']}: evidence missing {key}")
            published = datetime.fromisoformat(str(item["published_at_utc"]).replace("Z", "+00:00"))
            if published.utcoffset() is None:
                raise ValueError(f"{row['ticker']}: evidence timestamp must include offset")
            if published > cutoff.astimezone(published.tzinfo):
                raise ValueError(f"{row['ticker']}: future leakage in evidence {item['ref']}")

    def run(self) -> dict[str, Any]:
        try:
            self._transition(RuntimeState.RESTORE)
            self._validate_run_metadata()

            self._transition(RuntimeState.DATA_HEALTH)
            eligible = self._eligible_universe()
            self._validate_coverage(eligible)

            self._transition(RuntimeState.MARKET_REGIME)
            regime = self.payload.get("market_regime")
            if regime not in {"RISK_ON", "NEUTRAL", "RISK_OFF", "DISLOCATION", "UNKNOWN"}:
                raise ValueError("market_regime invalid or missing")
            if not self.payload.get("market_regime_engine_version"):
                raise ValueError("market_regime_engine_version missing")

            self._transition(RuntimeState.UNIVERSE_FREEZE)
            universe_artifact = {
                "run_id": self.payload["run"]["run_id"],
                "snapshot_ref": self.payload["run"]["snapshot_ref"],
                "tickers": [r["ticker"] for r in eligible],
                "rows": eligible,
            }
            self.universe_hash = self._sha256(universe_artifact)

            self._transition(RuntimeState.DETECT)
            cutoff = self.payload["run"]["cutoff_et"]
            for row in eligible:
                self._validate_evidence(row, cutoff)

            self._transition(RuntimeState.EVIDENCE)
            self._transition(RuntimeState.THESIS)
            self._transition(RuntimeState.CHALLENGE)

            self._transition(RuntimeState.RANK)
            top20 = rank_top20(eligible)

            self._transition(RuntimeState.COMPRESSION)
            top5 = rank_top5(top20)

            self._transition(RuntimeState.EXECUTION)
            for row in top20:
                row.setdefault("execution_status", "NOT_EVALUATED")

            self._transition(RuntimeState.PREDICTION_FREEZE)
            prediction = {
                "contract": asdict(CONTRACT),
                "run": self.payload["run"],
                "market_regime": regime,
                "market_regime_engine_version": self.payload["market_regime_engine_version"],
                "universe_hash": self.universe_hash,
                "top20": top20,
                "top5_tickers": [r["ticker"] for r in top5],
            }
            self.prediction_hash = self._sha256(prediction)
            prediction["prediction_hash"] = self.prediction_hash

            self._transition(RuntimeState.WRITE_READY)
            return {
                "outcome": RunOutcome.PREDICTION_WRITE_READY.value,
                "state": self.state.value,
                "official_prediction": False,
                "persistence_required": True,
                "universe_hash": self.universe_hash,
                "prediction_hash": self.prediction_hash,
                "prediction": prediction,
                "audit": self.audit,
                "errors": [],
            }
        except ValueError as exc:
            message = str(exc)
            outcome = RunOutcome.INVALID_EVIDENCE if "evidence" in message or "leakage" in message else RunOutcome.INVALID_DATA
            return self._invalidate(outcome, message)

    @classmethod
    def close_after_readback(cls, result: dict[str, Any], readback_prediction_hash: str | None) -> dict[str, Any]:
        """Only this transition can mark a prediction official."""
        out = copy.deepcopy(result)
        expected = out.get("prediction_hash")
        prediction = out.get("prediction")
        if out.get("state") != RuntimeState.WRITE_READY.value or out.get("outcome") != RunOutcome.PREDICTION_WRITE_READY.value:
            out["outcome"] = RunOutcome.INVALID_PERSISTENCE.value
            out["state"] = RuntimeState.INVALID.value
            out["official_prediction"] = False
            out.setdefault("errors", []).append("Only WRITE_READY prediction can be closed")
            return out
        if not isinstance(prediction, dict) or not expected:
            out["outcome"] = RunOutcome.INVALID_PERSISTENCE.value
            out["state"] = RuntimeState.INVALID.value
            out["official_prediction"] = False
            out.setdefault("errors", []).append("Frozen prediction payload/hash missing")
            return out
        embedded = prediction.get("prediction_hash")
        recomputed = cls.recompute_prediction_hash(prediction)
        if embedded != expected or recomputed != expected:
            out["outcome"] = RunOutcome.INVALID_PERSISTENCE.value
            out["state"] = RuntimeState.INVALID.value
            out["official_prediction"] = False
            out.setdefault("errors", []).append("Frozen prediction mutated after hash")
            return out
        if readback_prediction_hash != expected:
            out["outcome"] = RunOutcome.INVALID_PERSISTENCE.value
            out["state"] = RuntimeState.INVALID.value
            out["official_prediction"] = False
            out.setdefault("errors", []).append("External Brain readback hash mismatch")
            return out
        out["outcome"] = RunOutcome.VALID_PREDICTION.value
        out["state"] = RuntimeState.CLOSED.value
        out["official_prediction"] = True
        out["persistence_required"] = False
        out.setdefault("audit", []).append({"state": RuntimeState.CLOSED.value, "detail": "READBACK_HASH_MATCH"})
        return out
