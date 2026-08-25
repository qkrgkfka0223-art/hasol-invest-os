# HASOL Full-Market Quant Engine v1

Status as of 2026-08-25: **BUILT / CI VERIFIED / HISTORICAL SIP SCALE VERIFIED / NOT PRODUCTION**.

## Role

GitHub is the deterministic compute/code/artifact layer. It does not make the final investment judgment.

```text
Alpaca historical SIP -> Full-Market Quant -> full_rank / quant_top50
Web Event Detector    -> event candidates
                              |
                              v
                         HASOL fusion
                              |
                              v
                     09:25 ET Top20/Top5
```

## Locked specs

- Feature spec: `HASOL-QF-v1.0`
- Rank spec: `HASOL-QR-v1.0`
- Completed-session OHLCV / volume / trade_count / VWAP canonical feed: historical consolidated SIP
- IEX volume is not canonical EOD market volume.
- Current production state remains `NOT_PRODUCTION`.

## Quant artifacts

A successful official run emits:

```text
run_manifest.json
data_quality.json
reference_universe.csv
reference_universe_meta.json
universe_snapshot.csv
features.csv
full_rank.csv
quant_top50.csv
```

The run is rejected when coverage is below 98% or fewer than 50 valid ranked candidates exist.

## Reference universe verification

Latest verified point-in-time broad reference artifact:

- symbols: **5,617 unique**
- blank tickers: **0**
- duplicates: **0**
- literal ticker `NA`: preserved
- special CQS-style `^`, `$`, `/` symbols: excluded
- SHA256: `732005f9b76d5e3687e3574da194717d48437ebc803c3ecc26d48e49e6e9778d`

This is a broad non-ETF reference universe, not yet the final guaranteed COMMON_STOCK universe. Final eligibility still requires Alpaca tradability, liquidity gates, and deterministic security-type purity.

## Historical SIP scale test

Completed-session stress test for **2026-08-24**:

- requested: **5,617**
- symbols returning a SIP daily bar: **5,545**
- no-bar: **72**
- coverage: **98.71817696%**
- scale gate: **PASS**

This proves broad full-market historical SIP daily-bar retrieval scale. It does **not** prove final security-type purity, Web event recall, premarket data freshness, or the full prediction E2E.

## Bugs found and fixed during verification

1. Literal ticker `NA` was interpreted by pandas as a null token.
   - Fixed with explicit non-NA string parsing.
   - Regression test added.
   - Historical SIP bar for `NA` was independently confirmed.

2. Preferred-style symbol `ALL$B` contaminated the broad reference and caused a multi-symbol Alpaca request to return HTTP 400.
   - `^`, `$`, `/` special-symbol forms are now excluded from the reference layer.

3. A single invalid symbol could kill an entire market batch.
   - Explicit Alpaca HTTP 400 `invalid symbol` errors are recursively isolated.
   - Single invalid symbols are recorded in `data_quality.invalid_symbols`.
   - Auth, entitlement, rate, server, and network failures are **not** hidden by this isolation logic.

## GitHub Actions

Workflow: `.github/workflows/full-market-quant.yml`

Verified before the credential gate:

- checkout: PASS
- Python/dependency setup: PASS
- unit tests: PASS
- CLI smoke: PASS
- point-in-time reference artifact: PASS
- artifact upload: PASS

Current manual runtime blocker:

```text
ALPACA_API_KEY_ID
ALPACA_API_SECRET_KEY
```

These must be configured as GitHub repository Actions secrets. Credentials must never be committed to source code, artifacts, Sheets, or chat logs.

## Remaining production blockers

1. deterministic security-type purity for the final COMMON_STOCK universe
2. full-market Web event-first collector / mapping / dedupe E2E
3. canonical analyst consensus and estimate-revision source
4. reliable 09:25 ET premarket freshness/coverage gate
5. HASOL fusion -> Top20/Top5 freeze -> Sheet readback
6. three clean timed E2E cycles + restore/review gates

Until those pass, this engine is a verified compute component, not a production prediction system.
