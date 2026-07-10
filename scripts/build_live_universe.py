from __future__ import annotations

import csv
import io
import urllib.request
from pathlib import Path

NASDAQ_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
USER_AGENT = "HASOL-Invest-OS/1.0 contact=qkrgkfka0223@gmail.com"


def download(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def clean_symbol(symbol: str) -> str | None:
    symbol = symbol.strip().upper().replace(".", "-")
    if not symbol or len(symbol) > 6:
        return None
    if any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ-" for ch in symbol):
        return None
    # Exclude common preferred/warrant/unit/right suffix patterns.
    if symbol.endswith(("W", "WS", "U", "R", "RT", "P")):
        return None
    return symbol


def parse_nasdaq(text: str) -> list[str]:
    rows = csv.DictReader(io.StringIO(text), delimiter="|")
    out: list[str] = []
    for row in rows:
        if row.get("Test Issue") != "N" or row.get("ETF") != "N":
            continue
        symbol = clean_symbol(row.get("Symbol", ""))
        if symbol:
            out.append(symbol)
    return out


def parse_other(text: str) -> list[str]:
    rows = csv.DictReader(io.StringIO(text), delimiter="|")
    out: list[str] = []
    for row in rows:
        if row.get("Test Issue") != "N" or row.get("ETF") != "N":
            continue
        symbol = clean_symbol(row.get("ACT Symbol", ""))
        if symbol:
            out.append(symbol)
    return out


def main() -> None:
    symbols = sorted(set(parse_nasdaq(download(NASDAQ_URL)) + parse_other(download(OTHER_URL))))
    # Diversify alphabetically rather than taking only the first block.
    target = 450
    if len(symbols) < 300:
        raise RuntimeError(f"Universe too small: {len(symbols)}")
    step = len(symbols) / target
    selected = [symbols[min(int(i * step), len(symbols) - 1)] for i in range(target)]
    selected = list(dict.fromkeys(selected))
    for benchmark in ("SPY", "QQQ"):
        if benchmark not in selected:
            selected.append(benchmark)
    output = Path("universe_live.csv")
    output.write_text("ticker\n" + "\n".join(selected) + "\n", encoding="utf-8")
    print(f"Built {len(selected)}-ticker live universe at {output}")


if __name__ == "__main__":
    main()
