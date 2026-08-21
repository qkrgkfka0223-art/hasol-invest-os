from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RuntimeState(str, Enum):
    BOOT = "BOOT"
    RESTORE = "RESTORE"
    DATA_HEALTH = "DATA_HEALTH"
    MARKET_REGIME = "MARKET_REGIME"
    UNIVERSE_FREEZE = "UNIVERSE_FREEZE"
    DETECT = "DETECT"
    EVIDENCE = "EVIDENCE"
    THESIS = "THESIS"
    CHALLENGE = "CHALLENGE"
    RANK = "RANK"
    COMPRESSION = "COMPRESSION"
    EXECUTION = "EXECUTION"
    PREDICTION_FREEZE = "PREDICTION_FREEZE"
    WRITE_READY = "WRITE_READY"
    CLOSED = "CLOSED"
    INVALID = "INVALID"


class RunOutcome(str, Enum):
    VALID_PREDICTION = "VALID_PREDICTION"
    VALID_NO_EXECUTION = "VALID_NO_EXECUTION"
    VALID_NO_CANDIDATE = "VALID_NO_CANDIDATE"
    INVALID_DATA = "INVALID_DATA"
    INVALID_EVIDENCE = "INVALID_EVIDENCE"
    INVALID_PERSISTENCE = "INVALID_PERSISTENCE"
    DEGRADED_RESEARCH_ONLY = "DEGRADED_RESEARCH_ONLY"


@dataclass(frozen=True)
class StrategyContract:
    strategy_version: str = "HASOL-PREDICTOR-v1.1-CANDIDATE"
    ruleset_version: str = "HASOL-RULESET-v1.0"
    runtime_version: str = "HASOL-MODEL-LOOP-v3.0-CANDIDATE"
    min_price: float = 3.0
    min_adv20_usd: float = 10_000_000.0
    min_completed_sessions: int = 20
    required_market_coverage: float = 0.98
    min_valid_positive_engines: int = 4
    top20_count: int = 20
    top5_count: int = 5
    allowed_exchanges: tuple[str, ...] = ("NASDAQ", "NYSE", "NYSE_AMERICAN")
    positive_engines: tuple[str, ...] = (
        "earnings_expectations",
        "future_flow_event",
        "price_rs",
        "supply_demand",
        "quality",
        "market_regime",
    )
    compression_components: tuple[str, ...] = (
        "flow_clarity",
        "evidence_freshness",
        "price_acceptance",
        "next_buyer_clarity",
        "priced_in_asymmetry",
        "risk_resilience",
    )
    compression_allowed_scores: tuple[int, ...] = (0, 25, 50, 75, 100)


CONTRACT = StrategyContract()
