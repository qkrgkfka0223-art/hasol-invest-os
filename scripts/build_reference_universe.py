from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from hasol_quant.universe import load_reference_universe


def main() -> None:
    parser = argparse.ArgumentParser(description="Build HASOL point-in-time exchange reference universe")
    parser.add_argument("--output-dir", default="output_quant")
    args = parser.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    ref = load_reference_universe().sort_values("ticker").reset_index(drop=True)
    csv_path = out / "reference_universe.csv"
    ref.to_csv(csv_path, index=False)
    sha256 = hashlib.sha256(csv_path.read_bytes()).hexdigest()

    meta = {
        "schema": "HASOL-REFERENCE-UNIVERSE-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "count": int(len(ref)),
        "sha256": sha256,
        "sources": [
            "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
            "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
        ],
        "note": "Reference only. Final tradable/liquidity universe requires Alpaca tradability + market liquidity gates.",
    }
    (out / "reference_universe_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
