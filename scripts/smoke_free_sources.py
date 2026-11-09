"""Network evidence for no-key US equity data options (experiment only).

Run from GitHub Actions; emits machine-readable PASS/PARTIAL/FAIL observations.
Never freezes a prediction and never uploads a user's personal data.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

SYMBOL_LISTS = {
    "NASDAQ": "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
    "OTHER": "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
}
EXTERNAL_REFERENCE = {
    "SEC_SUBMISSIONS": "https://data.sec.gov/submissions/CIK0000320193.json",
    "SEC_COMPANY_EXCHANGE": "https://www.sec.gov/files/company_tickers_exchange.json",
}


def parse_symbols(payload: str, kind: str) -> dict:
    lines = [z for z in payload.splitlines() if z.strip()]
    if len(lines) < 2:
        raise ValueError("empty symbol file")
    parts = lines[0].split("|")
    expected = {"Symbol", "ETF", "Test Issue"} if kind == "NASDAQ" else {"ACT Symbol", "ETF", "Test Issue", "Exchange"}
    if not expected.issubset(parts):
        raise ValueError(f"unexpected {kind} directory header: {parts[:12]}")
    i = {key: parts.index(key) for key in expected}
    records = []
    for line in lines[1:]:
        if line.startswith("File Creation Time"):
            continue
        z = line.split("|")
        if len(z) <= max(i.values()):
            continue
        if z[i["ETF"]] != "N" or z[i["Test Issue"]] != "N":
            continue
        if kind == "OTHER" and z[i["Exchange"]] not in {"N", "A"}:
            continue
        records.append(z[i["Symbol"]] if kind == "NASDAQ" else z[i["ACT Symbol"]])
    return {
        "directory_type": kind,
        "non_etf_non_test_listings_n": len(records),
        "sample_symbols": records[:8],
        "directory_file_creation": next((x for x in lines if x.startswith("File Creation Time")), "UNKNOWN"),
        "limitations": "NOT VERIFIED COMMON STOCK, SPAC, ADR, WARRANT OR 20D ELIGIBILITY",
    }


def _request_json(url: str) -> dict:
    # SEC guidance recommends an identifiable bot and contact. Use public project
    # issue tracker; no invented administrator email, login, or token.
    headers = {
        "User-Agent": "HASOL-Invest-OS research (https://github.com/qkrgkfka0223-art/hasol-invest-os/issues)",
        "Accept": "application/json",
    }
    r = requests.get(url, headers=headers, timeout=18)
    r.raise_for_status()
    return {"http_status": r.status_code, "bytes": len(r.content), "data": r.json()}


def probe() -> dict:
    out = {
        "measured_utc": datetime.now(timezone.utc).isoformat(),
        "provider_tests": {},
        "no_api_key_supplied": True,
        "production_suitability": "DETECTION_ONLY_NOT_FROZEN_VALIDATED",
    }
    coarse_common = {}
    for name, url in SYMBOL_LISTS.items():
        start = time.monotonic()
        try:
            r = requests.get(url, timeout=18, headers={"User-Agent": "HASOL research (https://github.com/qkrgkfka0223-art/hasol-invest-os)"})
            r.raise_for_status()
            parsed = parse_symbols(r.text, name)
            # Only a provisional textual screen. Does NOT establish SPAC/common
            # security status; issuer-level type verification is still required.
            lines = r.text.splitlines()
            columns = lines[0].split("|")
            sym_col = columns.index("Symbol" if name == "NASDAQ" else "ACT Symbol")
            desc_col = columns.index("Security Name")
            etf_col = columns.index("ETF")
            test_col = columns.index("Test Issue")
            exc_col = columns.index("Exchange") if name == "OTHER" else None
            suspect = re.compile(
                r"warrant|rights?\\b|units?\\b|preferred|depositary|acquisition corp|"
                r"exchange.traded|\\bnote\\b|\\bbond\\b|\\btrust\\b|"
                r"american deposit|senior notes", re.IGNORECASE
            )
            picked = []
            for line in lines[1:]:
                row = line.split("|")
                if len(row) <= max(sym_col, desc_col, etf_col, test_col, exc_col or 0):
                    continue
                symbol = row[sym_col]
                if (row[etf_col] == "N" and row[test_col] == "N"
                    and (exc_col is None or row[exc_col] in ("A", "N"))
                    and re.fullmatch(r"[A-Z][A-Z0-9]{0,6}", symbol)
                    and not suspect.search(row[desc_col])):
                    picked.append(symbol)
            coarse_common[name] = sorted(set(picked))
            parsed["provisional_text_screen_n"] = len(coarse_common[name])
            parsed.update({"state": "PASS_REFERENCE_ONLY", "http_status": r.status_code})
            out["provider_tests"]["NASDAQ_DIR_"+name] = parsed
        except Exception as exc:
            out["provider_tests"]["NASDAQ_DIR_"+name] = {"state": "FAIL", "error_type": type(exc).__name__, "error": str(exc)[:180]}
        out["provider_tests"]["NASDAQ_DIR_"+name]["elapsed_seconds"] = round(time.monotonic()-start, 2)
    for name, url in EXTERNAL_REFERENCE.items():
        start = time.monotonic()
        try:
            res = _request_json(url)
            data = res["data"]
            if name == "SEC_SUBMISSIONS":
                sample = {"CIK": data.get("cik"), "name": data.get("name"), "filings_recent_n": len(data.get("filings", {}).get("recent", {}).get("accessionNumber", []))}
            else:
                sample = {"fields": data.get("fields", []), "securities_n": len(data.get("data", []))}
            out["provider_tests"][name] = {"state": "PASS_REFERENCE_ONLY", "http_status": res["http_status"], "bytes": res["bytes"], **sample}
        except Exception as exc:
            out["provider_tests"][name] = {"state": "FAIL", "error_type": type(exc).__name__, "error": str(exc)[:180]}
        out["provider_tests"][name]["elapsed_seconds"] = round(time.monotonic()-start, 2)
    start = time.monotonic()
    syms = ["AAPL", "MSFT", "NVDA", "AAOI", "IONQ", "SPY", "TSLA", "MRNA"]
    try:
        # Restrict to already completed dates so a future bar cannot leak.
        bars = yf.download(syms, start="2026-10-19", end="2026-11-07", interval="1d",
                           auto_adjust=False, actions=False, progress=False,
                           threads=False, timeout=25)
        from hasol_quant.yahoo_client import _normalize_download
        rows = _normalize_download(bars, syms)
        clean = rows.dropna(subset=["timestamp", "high", "close", "volume"])
        got = sorted(clean["ticker"].unique().tolist())
        counts = {str(t): int((clean["ticker"] == t).sum()) for t in syms}
        last = {str(t): str(clean.loc[clean["ticker"] == t, "timestamp"].max().date())
                if t in got else "UNKNOWN" for t in syms}
        out["provider_tests"]["YFINANCE_DAILY_8"] = {
            "state": "PASS_DETECTION_ONLY" if len(got) == len(syms) else "PARTIAL",
            "requested_n": len(syms), "returned_n": len(got), "bar_counts": counts,
            "latest_bar_dates": last,
            "notes": "YAHOO_UNOFFICIAL_NOT_CONSOLIDATED_SIP_AND_NOT_CANONICAL",
        }
    except Exception as exc:
        out["provider_tests"]["YFINANCE_DAILY_8"] = {
            "state": "FAIL", "error_type": type(exc).__name__, "error": str(exc)[:200],
            "requested_n": len(syms),
        }
    out["provider_tests"]["YFINANCE_DAILY_8"]["elapsed_seconds"] = round(time.monotonic()-start, 2)
    # Single modest batch from both official exchanges, spaced across the
    # ticker alphabet; no 7,000-symbol Yahoo scraping or aggressive retry.
    src = [coarse_common.get("NASDAQ", []), coarse_common.get("OTHER", [])]
    sampled = []
    for names in src:
        if names:
            sampled += [names[round((len(names)-1)*i/39)] for i in range(40)]
    sampled = sorted(set(sampled))
    start = time.monotonic()
    try:
        if len(sampled) < 40:
            raise ValueError("Nasdaq/NYSE symbol directories did not yield sufficient candidates")
        raw = yf.download(sampled, start="2026-09-15", end="2026-11-07", interval="1d",
                          auto_adjust=False, actions=False, progress=False,
                          threads=False, timeout=25)
        from hasol_quant.yahoo_client import _normalize_download
        normalized = _normalize_download(raw, sampled)
        valid = normalized.dropna(subset=["timestamp", "high", "close", "volume"])
        coverage = sorted(set(valid["ticker"].tolist()))
        mature = [t for t in sampled if int((valid["ticker"] == t).sum()) >= 20]
        prelim_eligible = []
        outdated = []
        for t in sampled:
            rows = valid.loc[valid["ticker"] == t].sort_values("timestamp").tail(20)
            if len(rows) < 20:
                continue
            if rows["timestamp"].max().date().isoformat() != "2026-11-06":
                outdated.append(t)
                continue
            avg_dollar_volume = float((rows["close"] * rows["volume"]).mean())
            if float(rows.iloc[-1]["close"]) >= 3.0 and avg_dollar_volume >= 10_000_000:
                prelim_eligible.append(t)
        out["provider_tests"]["YFINANCE_SPREAD80"] = {
            "state": "PASS_SAMPLE_ONLY" if len(mature) == len(sampled) else "PARTIAL",
            "requested_n": len(sampled), "returned_n": len(coverage),
            "complete_20_sessions_n": len(mature),
            "prelim_price_and_adtv20_pass_n": len(prelim_eligible),
            "stale_asof_nov06_symbols": outdated[:20],
            "missing_symbols": sorted(set(sampled)-set(coverage))[:20],
            "sampling": "40 NASDAQ + 40 NYSE/NYSE_AMERICAN alphabet-spaced symbols after PROVISIONAL text filter",
            "limitations": "SAMPLE ONLY; ADTV uses Yahoo close*volume, security type and SPAC still unverified, not SIP, no premarket quote",
        }
    except Exception as exc:
        out["provider_tests"]["YFINANCE_SPREAD80"] = {
            "state": "FAIL", "error_type": type(exc).__name__,
            "error": str(exc)[:200], "requested_n": len(sampled),
        }
    out["provider_tests"]["YFINANCE_SPREAD80"]["elapsed_seconds"] = round(time.monotonic()-start, 2)
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=Path("output_free_source_probe/probe.json"))
    a = p.parse_args()
    data = probe()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("HASOL_FREE_DATA_PROBE=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
