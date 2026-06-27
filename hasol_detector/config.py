from dataclasses import dataclass, field
from typing import Dict, List

VERSION = "1.2"

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
    top20_quotas: Dict[str, int] = field(default_factory=lambda: {
        "mega_cap": 2,
        "large_cap": 3,
        "mid_cap": 7,
        "small_cap": 7,
        "micro_cap": 3,
        "nano_cap": 0,
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
    "M&A": 17,
    "IPO": 14,
    "POLICY": 13,
    "DEFENSE": 13,
    "SPACE": 12,
    "PRODUCT": 10,
    "CAPEX": 12,
    "SUPPLY_SHORTAGE": 12,
    "INSIDER_BUY": 14,
    "GOV_CONTRACT": 13,
    "AI_INFRA": 15,
    "DATA_CENTER": 14,
    "SHORT_SQUEEZE": 4,
    "NONE": 0,
}

AXIS_KEYWORDS = {
    "AI_INFRA": ["AI", "compute", "GPU", "data center", "AMD", "NVIDIA", "infrastructure"],
    "DEFENSE": ["defense", "drone", "military", "DoD", "Army", "Navy", "contract"],
    "BIOTECH": ["FDA", "Phase", "trial", "clinical", "biotech", "drug"],
    "ENERGY": ["battery", "solar", "energy", "storage", "grid"],
    "SEC_FLOW": ["Form 4", "13D", "insider", "activist"],
}
