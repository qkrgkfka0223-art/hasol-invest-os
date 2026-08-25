from __future__ import annotations

import argparse
from pathlib import Path

from hasol_quant.runner import run_full_market_quant


def main() -> None:
    p = argparse.ArgumentParser(description="Run HASOL full-market deterministic Quant Engine.")
    p.add_argument("--output-dir", default="output_quant")
    p.add_argument("--feed", default="sip", choices=["sip", "iex", "delayed_sip"])
    p.add_argument("--lookback-calendar-days", type=int, default=120)
    args = p.parse_args()
    manifest = run_full_market_quant(Path(args.output_dir), feed=args.feed, lookback_calendar_days=args.lookback_calendar_days)
    print(f"HASOL Quant run complete: {manifest['run_id']}")


if __name__ == "__main__":
    main()
