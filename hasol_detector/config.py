from dataclasses import dataclass, field
from typing import Dict, List

VERSION = "1.4"

@dataclass(frozen=True)
class CapBucketRule:
    name: str
    min_cap: float
    max_cap: float

@dataclass(frozen=True)
class HasolConfig:
    min_price: float = 2.0
    min_dollar_volume: float = 5_000_000
    min_market_cap_for_top: float = 50_000_000
    rel_volume_floor: float = 1.2
    min_history_bars: int = 50
    max_live_tickers: int = 500
    benchmark_tickers: tuple[str, str] = ("SPY", "QQQ")
    require_web_validation_for_execution: bool = True
    micro_nano_execution_locked: bool = True
    stale_news_days: int = 10
    sec_cluster_min_forms: int = 2

    # v1.4: code detects phases; HASOL interprets whether the phase is actionable.
    early_signal_min_change: float = 8.0
    early_signal_max_change: float = 35.0
    hot_signal_max_change: float = 80.0
    climax_change: float = 80.0
    early_relvol_min: float = 1.8
    early_relvol_max_for_execution: float = 8.0
    max_execution_change_pct: float = 25.0
    max_execution_relvol: float = 8.0

    top20_quotas: Dict[str, int] = field(default_factory=lambda: {
        "mega_cap": 2,
        "large_cap": 3,
        "mid_cap": 7,
        "small_cap": 7,
        "micro_cap": 4,
        "nano_cap": 1,
        "unknown": 1,
    })
    cap_rules: List[CapBucketRule] = field(default_factory=lambda: [
        CapBucketRule("mega_cap", 200_000_000_000, float("inf")),
        CapBucketRule("large_cap", 10_000_000_000, 200_000_000_000),
        CapBucketRule("mid_cap", 2_000_000_000, 10_000_000_000),
        CapBucketRule("small_cap", 300_000_000, 2_000_000_000),
        CapBucketRule("micro_cap", 50_000_000, 300_000_000),
        CapBucketRule("nano_cap", 0, 50_000_000),
    ])

EVENT_WEIGHTS = {
    "EARNINGS": 18,
    "FDA": 18,
    "CLINICAL_SUCCESS": 19,
    "BLA_ACCEPTED": 18,
    "BIOTECH_LICENSE": 16,
    "M&A": 17,
    "IPO": 14,
    "POLICY": 13,
    "DEFENSE": 13,
    "SPACE": 12,
    "PRODUCT": 10,
    "CAPEX": 12,
    "SUPPLY_SHORTAGE": 12,
    "INSIDER_BUY": 14,
    "SEC_CLUSTER": 16,
    "OWNERSHIP_CHANGE": 14,
    "COMPLIANCE_RECOVERY": 12,
    "GOV_CONTRACT": 13,
    "AI_INFRA": 15,
    "DATA_CENTER": 14,
    "FAMOUS_PARTNER": 13,
    "SHORT_SQUEEZE": 4,
    "NONE": 0,
}

AXIS_KEYWORDS = {
    "AI_INFRA": ["AI", "compute", "GPU", "data center", "AMD", "NVIDIA", "infrastructure", "Starlink"],
    "DEFENSE": ["defense", "drone", "military", "DoD", "Army", "Navy", "contract"],
    "BIOTECH": ["FDA", "Phase", "trial", "clinical", "biotech", "drug", "BLA", "endpoint"],
    "ENERGY": ["battery", "solar", "energy", "storage", "grid"],
    "SPACE": ["space", "lunar", "satellite", "launch", "NASA", "SpaceX", "Artemis", "Starlink"],
    "SEC_FLOW": ["Form 3", "Form 4", "13D", "13G", "insider", "activist", "large holder"],
}

FAMOUS_PARTNER_KEYWORDS = [
    "Starlink", "SpaceX", "NASA", "Artemis", "AMD", "NVIDIA", "Microsoft", "Amazon", "Google",
    "DoD", "Army", "Navy", "Air Force", "FDA"
]

BIOTECH_EXPANSION_KEYWORDS = [
    "BLA accepted", "resubmitted BLA", "late-stage trial", "met primary endpoint", "primary endpoint met",
    "exclusive rights", "licensing deal", "license agreement", "Phase 3", "Type C meeting", "appeal win"
]
