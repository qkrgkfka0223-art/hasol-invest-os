from __future__ import annotations

from dataclasses import dataclass
import os

FEATURE_SPEC_VERSION = "HASOL-QF-v1.0"
RANK_SPEC_VERSION = "HASOL-QR-v1.0"

NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"

DEFAULT_DATA_BASE_URL = "https://data.alpaca.markets"
DEFAULT_TRADING_BASE_URL = "https://paper-api.alpaca.markets"

@dataclass(frozen=True)
class Settings:
    api_key: str
    api_secret: str
    data_base_url: str = DEFAULT_DATA_BASE_URL
    trading_base_url: str = DEFAULT_TRADING_BASE_URL
    feed: str = "sip"
    batch_size: int = 200
    request_limit: int = 10_000
    timeout_seconds: int = 45
    max_retries: int = 5

    @classmethod
    def from_env(cls, feed: str = "sip") -> "Settings":
        key = os.getenv("ALPACA_API_KEY_ID", "").strip()
        secret = os.getenv("ALPACA_API_SECRET_KEY", "").strip()
        if not key or not secret:
            raise RuntimeError(
                "Missing ALPACA_API_KEY_ID / ALPACA_API_SECRET_KEY. "
                "Use GitHub Actions secrets; never hard-code credentials."
            )
        return cls(
            api_key=key,
            api_secret=secret,
            data_base_url=os.getenv("ALPACA_DATA_BASE_URL", DEFAULT_DATA_BASE_URL).rstrip("/"),
            trading_base_url=os.getenv("ALPACA_TRADING_BASE_URL", DEFAULT_TRADING_BASE_URL).rstrip("/"),
            feed=feed,
            batch_size=int(os.getenv("HASOL_BATCH_SIZE", "200")),
            request_limit=int(os.getenv("HASOL_REQUEST_LIMIT", "10000")),
            timeout_seconds=int(os.getenv("HASOL_HTTP_TIMEOUT", "45")),
            max_retries=int(os.getenv("HASOL_MAX_RETRIES", "5")),
        )
