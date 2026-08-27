from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DEPRECATED: full-market Alpaca Quant path is disabled. Use scripts.run_web_candidate_quant."
    )
    parser.parse_args()
    raise SystemExit(
        "DEPRECATED_FULL_MARKET_ALPACA_PATH: GitHub no longer requires Alpaca keys. "
        "Use python -m scripts.run_web_candidate_quant."
    )


if __name__ == "__main__":
    main()
