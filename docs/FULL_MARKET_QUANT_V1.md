# HASOL Full-Market Quant Engine v1

## Role

This engine is not HASOL's investment judgment. It performs deterministic full-market calculation:

`Historical SIP -> listed/tradable universe -> features -> liquidity gate -> full rank -> Quant Top50`

HASOL later fuses Quant candidates with Web events, expectations, and price reaction.

## Canonical data policy

- Completed-session OHLCV / volume / trade count / VWAP: Alpaca historical SIP.
- IEX volume must not be used as canonical full-market EOD volume.
- Before 16:20 ET a manual run excludes the current ET calendar day, so an in-progress session cannot leak into the rank.
- API failures are errors, never zero values.
- Every run emits feed/version/commit lineage.

## Feature spec

`HASOL-QF-v1.0`: 1/3/5/10/20/60D returns, 5/20/60D SPY RS, ADV20, volume ratio/z-score, gap, close location, ATR14%, compression, distance to 20D/60D highs, breakout20, EMA20 extension.

## Universe gates

- US listed non-test non-ETF reference symbols.
- Intersect active/tradable Alpaca assets.
- Obvious preferred/warrant/unit/right/blank-check names excluded.
- Latest regular close >= $3.
- ADV20 >= $10M.
- >= 20 completed sessions.

## Required outputs

`run_manifest.json`, `data_quality.json`, `universe_snapshot.csv`, `features.csv`, `full_rank.csv`, `quant_top50.csv`.

## Integrity gates

- market-data coverage >= 98%
- exactly 50 valid Quant candidates
- deterministic feature/rank version
- Git commit SHA and artifact hashes recorded

## GitHub Actions

Workflow: `HASOL Full-Market Quant v1`.

Required repository secrets: `ALPACA_API_KEY_ID`, `ALPACA_API_SECRET_KEY`.

Manual CLI: `python -m scripts.run_full_market_quant --feed sip --output-dir output_quant`.

Never commit credentials.
