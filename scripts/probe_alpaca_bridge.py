from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def get_json(url: str, key: str, secret: str):
    request = urllib.request.Request(
        url,
        headers={
            "APCA-API-KEY-ID": key,
            "APCA-API-SECRET-KEY": secret,
            "Accept": "application/json",
            "User-Agent": "HASOL-v3-bridge-probe/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"HTTP {exc.code} for {url.split('?')[0]}: {body}") from exc


def main() -> int:
    key = os.environ.get("APCA_API_KEY_ID", "").strip()
    secret = os.environ.get("APCA_API_SECRET_KEY", "").strip()
    if not key or not secret:
        print("HASOL_BRIDGE_STATUS=MISSING_GITHUB_ALPACA_SECRETS")
        print("Required GitHub secrets: APCA_API_KEY_ID, APCA_API_SECRET_KEY")
        return 3

    assets_url = "https://paper-api.alpaca.markets/v2/assets?status=active&asset_class=us_equity"
    _, assets = get_json(assets_url, key, secret)
    if not isinstance(assets, list) or not assets:
        print("HASOL_BRIDGE_STATUS=ASSET_ENDPOINT_EMPTY")
        return 4

    params = urllib.parse.urlencode({
        "symbols": "AAPL,MSFT",
        "timeframe": "1Day",
        "start": "2026-08-17T00:00:00-04:00",
        "end": "2026-08-19T16:00:00-04:00",
        "limit": "100",
        "feed": "sip",
        "sort": "asc",
    })
    bars_url = f"https://data.alpaca.markets/v2/stocks/bars?{params}"
    _, market = get_json(bars_url, key, secret)
    bars = market.get("bars") if isinstance(market, dict) else None
    if not isinstance(bars, dict) or not bars:
        print("HASOL_BRIDGE_STATUS=MARKET_ENDPOINT_EMPTY")
        return 5

    record_count = sum(len(v) for v in bars.values() if isinstance(v, list))
    symbols = sorted(symbol for symbol, values in bars.items() if isinstance(values, list) and values)
    print("HASOL_BRIDGE_STATUS=PASS")
    print(f"ACTIVE_US_EQUITY_ASSET_COUNT={len(assets)}")
    print(f"SIP_PROBE_SYMBOLS={','.join(symbols)}")
    print(f"SIP_PROBE_RECORDS={record_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
