from __future__ import annotations

import time
from typing import Iterable

import pandas as pd
import requests

from .config import Settings


class AlpacaHTTPError(RuntimeError):
    def __init__(self, status_code: int, body: str, url: str):
        super().__init__(f"Alpaca HTTP {status_code}: {body[:500]} ({url})")
        self.status_code = status_code
        self.body = body
        self.url = url


class AlpacaClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.invalid_symbols: set[str] = set()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "APCA-API-KEY-ID": settings.api_key,
                "APCA-API-SECRET-KEY": settings.api_secret,
                "Accept": "application/json",
                "User-Agent": "HASOL-FullMarketQuant/1.0",
            }
        )

    def _request_json(self, url: str, params: dict | None = None) -> dict | list:
        last_error: Exception | None = None
        for attempt in range(self.settings.max_retries):
            try:
                resp = self.session.get(url, params=params, timeout=self.settings.timeout_seconds)
                if resp.status_code == 429:
                    time.sleep(min(60, 2 ** attempt))
                    continue
                if 500 <= resp.status_code < 600:
                    time.sleep(min(30, 2 ** attempt))
                    continue
                if resp.status_code >= 400:
                    raise AlpacaHTTPError(resp.status_code, resp.text, url)
                return resp.json()
            except AlpacaHTTPError:
                raise
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if attempt + 1 >= self.settings.max_retries:
                    break
                time.sleep(min(30, 2 ** attempt))
        raise RuntimeError(f"Alpaca request failed after retries: {url}") from last_error

    def list_active_assets(self) -> pd.DataFrame:
        payload = self._request_json(
            f"{self.settings.trading_base_url}/v2/assets",
            params={"status": "active", "asset_class": "us_equity"},
        )
        if not isinstance(payload, list):
            raise RuntimeError("Unexpected assets response shape.")
        rows = []
        for a in payload:
            rows.append(
                {
                    "ticker": str(a.get("symbol", "")).upper(),
                    "name": a.get("name"),
                    "exchange": a.get("exchange"),
                    "status": a.get("status"),
                    "tradable": bool(a.get("tradable")),
                    "fractionable": bool(a.get("fractionable")),
                    "shortable": bool(a.get("shortable")),
                    "easy_to_borrow": bool(a.get("easy_to_borrow")),
                }
            )
        return pd.DataFrame(rows)

    def _fetch_batch_pages(self, batch: list[str], start_iso: str, end_iso: str, adjustment: str) -> list[dict]:
        rows: list[dict] = []
        page_token: str | None = None
        while True:
            params = {
                "symbols": ",".join(batch),
                "timeframe": "1Day",
                "start": start_iso,
                "end": end_iso,
                "adjustment": adjustment,
                "feed": self.settings.feed,
                "sort": "asc",
                "limit": self.settings.request_limit,
            }
            if page_token:
                params["page_token"] = page_token
            payload = self._request_json(f"{self.settings.data_base_url}/v2/stocks/bars", params=params)
            bars = payload.get("bars", {}) if isinstance(payload, dict) else {}
            for ticker, items in bars.items():
                for bar in items or []:
                    rows.append(
                        {
                            "ticker": ticker.upper(),
                            "timestamp": bar.get("t"),
                            "open": bar.get("o"),
                            "high": bar.get("h"),
                            "low": bar.get("l"),
                            "close": bar.get("c"),
                            "volume": bar.get("v"),
                            "trade_count": bar.get("n"),
                            "vwap": bar.get("vw"),
                        }
                    )
            page_token = payload.get("next_page_token") if isinstance(payload, dict) else None
            if not page_token:
                break
        return rows

    def _fetch_batch_resilient(self, batch: list[str], start_iso: str, end_iso: str, adjustment: str) -> list[dict]:
        try:
            return self._fetch_batch_pages(batch, start_iso, end_iso, adjustment)
        except AlpacaHTTPError as exc:
            # One malformed/delisted symbol must not kill a 200-name market batch.
            # Only isolate Alpaca's explicit invalid-symbol client error; all other 4xx/5xx remain hard failures.
            if exc.status_code != 400 or "invalid symbol" not in exc.body.lower():
                raise
            if len(batch) == 1:
                self.invalid_symbols.add(batch[0])
                return []
            mid = len(batch) // 2
            return (
                self._fetch_batch_resilient(batch[:mid], start_iso, end_iso, adjustment)
                + self._fetch_batch_resilient(batch[mid:], start_iso, end_iso, adjustment)
            )

    def fetch_daily_bars(self, symbols: Iterable[str], start_iso: str, end_iso: str, adjustment: str = "all") -> pd.DataFrame:
        symbols = [s.upper() for s in symbols if s]
        all_rows: list[dict] = []
        for offset in range(0, len(symbols), self.settings.batch_size):
            batch = symbols[offset : offset + self.settings.batch_size]
            all_rows.extend(self._fetch_batch_resilient(batch, start_iso, end_iso, adjustment))
        df = pd.DataFrame(all_rows)
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
            for c in ["open", "high", "low", "close", "volume", "trade_count", "vwap"]:
                df[c] = pd.to_numeric(df[c], errors="coerce")
            df = df.dropna(subset=["ticker", "timestamp", "close"]).sort_values(["ticker", "timestamp"])
        return df
