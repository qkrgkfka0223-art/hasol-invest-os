from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from hasol_detector.us_universe import load_us_listed_universe


def canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256_json(value) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build unsampled HASOL v3 US listed universe snapshot")
    parser.add_argument("--output", type=Path, default=Path("artifacts/v3_universe.json"))
    parser.add_argument("--asof", default=None, help="Run date label YYYY-MM-DD; source itself is current Nasdaq Trader directory")
    args = parser.parse_args()

    frame = load_us_listed_universe(
        include_etfs=False,
        limit=None,
        sample=False,
        common_only=True,
    )
    if frame.empty:
        raise RuntimeError("Universe source returned zero rows")

    records = []
    for row in frame.to_dict(orient="records"):
        records.append({
            "ticker": str(row["ticker"]).upper().strip(),
            "company": str(row.get("company", "")).strip(),
            "exchange": str(row.get("exchange", "")).upper().strip(),
            "security_type": "COMMON_STOCK",
            "excluded_security_flag": False,
            "classification_source": "NASDAQ_TRADER_DIRECTORY_RULE_V1",
        })
    records = sorted(records, key=lambda x: x["ticker"])
    if len({r["ticker"] for r in records}) != len(records):
        raise RuntimeError("Universe contains duplicate tickers")

    artifact = {
        "schema": "HASOL-V3-UNIVERSE-SNAPSHOT-v1",
        "source": [
            "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
            "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
        ],
        "source_scope": "CURRENT_DIRECTORY_ONLY",
        "requested_asof": args.asof,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "sampled": False,
        "row_count": len(records),
        "records": records,
    }
    artifact["content_hash"] = sha256_json({k: v for k, v in artifact.items() if k != "created_at_utc"})

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "row_count": len(records),
        "sampled": False,
        "content_hash": artifact["content_hash"],
        "source_scope": artifact["source_scope"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
