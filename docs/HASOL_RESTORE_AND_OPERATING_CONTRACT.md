# HASOL Restore & Operating Contract

## North-star goal
HASOL exists to repeat one auditable loop on U.S. equities:

1. **Predict** before the target regular-session open which stocks have the strongest short-term upside setup.
2. **Freeze** the prediction before outcomes are known; never rewrite it with hindsight.
3. **Review** after the relevant session/horizon using canonical market facts.
4. **Grow** by recording misses, counter-hypotheses, evidence and forward-testable changes.
5. **Restore** the same strategy/state in a new ChatGPT conversation without relying on chat memory.

No component may claim guaranteed profit or a proven edge before the forward promotion gates are met.

## Tool ownership
- **Web / primary sources**: event discovery and verification (SEC/EDGAR, issuer IR, FDA/regulatory, direct earnings/guidance and approved wire sources).
- **GitHub**: deterministic code, candidate Quant, tests, immutable artifacts/checkpoints and lineage. GitHub must not own final market truth or final investment judgment.
- **Connected Alpaca in ChatGPT**: canonical final market validation, clock/calendar, security/tradability and market facts. Do not copy Alpaca credentials into GitHub or Sheets.
- **HASOL model in ChatGPT**: fusion and investment judgment: WHY_NOW, FUTURE_CAPITAL_FLOW, NEXT_BUYER, MARKET_MISSED, REFLECTION_LEVEL, PRICE_ACCEPTANCE, COUNTERCASE, INVALIDATION, CHASE_RISK.
- **HASOL_EXTERNAL_BRAIN Google Sheet**: durable decision memory, runs, frozen predictions, reviews, growth and execution records.
- **GPT automations**: scheduling, monitoring, orchestration and recovery. They are not the durable memory or bulk-compute layer.

## Durable restore anchors
- GitHub repository: `qkrgkfka0223-art/hasol-invest-os`
- External Brain title: `HASOL_EXTERNAL_BRAIN`
- External Brain spreadsheet id: `18a8F4LLIXzj491QjRAaoaS8ZPA0cE_XK7Uc4gkyayHc`
- Required tabs: `00_SYSTEM`, `01_RUNS`, `02_PREDICTIONS`, `03_REVIEW`, `04_GROWTH`, `05_EXECUTION`

## Restore protocol for a new conversation
When the user says **“HASOL 복원해”** (or equivalent), do not reconstruct from chat memory.

1. Read this file from current GitHub `main`.
2. Read External Brain spreadsheet metadata.
3. In `00_SYSTEM`, verify `BRAIN_ID`, `BRAIN_SCHEMA`, `SCHEMA_HEADER_HASH`, `SOURCE_OF_TRUTH`, `OPERATING_ARCHITECTURE`, `DATA_SOURCE_POLICY`, `PRIMARY_PREDICTION_CUTOFF`, `TOP20_SELECTION`, `RUN_INTEGRITY`, `REVIEW_INTEGRITY`, `LEARNING`, `STRATEGY_PROMOTION`, `LIVE_CONTROL_PLANE`, `LIVE_RUNTIME_SLA`, `HANDS_OFF_GATE`.
4. Read the latest valid/current rows from `01_RUNS`, `02_PREDICTIONS`, `03_REVIEW`, `04_GROWTH` and `05_EXECUTION` as applicable.
5. Read GitHub current `main`, the latest pre-open pointer/checkpoint and current Web/session health.
6. Query connected Alpaca clock/calendar before interpreting the current/next trading session.
7. Reconcile conflicts by source-of-truth order. Never guess missing state. If restore integrity fails, report `DEGRADED_RESTORE` and repair the durable state before producing an official prediction.
8. Only after these checks report `RESTORE_OK` and resume the daily loop.

## Daily prediction contract
- Information barrier: confirmed Alpaca regular-session open for the target U.S. trading day.
- Production PREMARKET Top20: **exactly 20 unique verified U.S. common-stock names** under `HASOL-TOP20-EXACT-v1`.
- Event-first candidates are primary. If fewer than 20 verified event candidates exist, use the approved deterministic liquid-watchlist/full-market Quant backstop with completed-session data.
- Backstop is candidate generation only. Every would-be official name still requires connected-Alpaca validation for security type, active/tradable state, liquidity/data quality and market facts.
- No ETF/ETN/fund/trust/unit/ADS/ADR/preferred/warrant/right/debt in the production cohort.
- No arbitrary padding and no fabricated event IDs.
- Top5 is exactly ranks 1-5 of the final exact Top20 and must pass the full HASOL judgment gate.
- If 20 verified names cannot be produced before open, fail closed as `TOP20_INCOMPLETE`; never manufacture a cohort.
- PREOPEN_CHECKPOINT is immutable/write-once. A later failed refresh cannot erase an earlier valid checkpoint.
- After open, Finalizer may only promote the latest valid checkpoint captured before open; no post-open reconstruction.

## Review and growth contract
- Review frozen cohorts only. Never score provisional or hindsight-rebuilt names as if they were official predictions.
- Evaluate at 1D/3D/5D/10D/20D as each horizon matures, including stock return, SPY/sector alpha, max runup/drawdown and actual-winner recall when a valid reference universe exists.
- Classify misses by pipeline stage and root cause; preserve counter-hypotheses.
- Growth changes are `OLD -> NEW + evidence/test + lineage` and must be forward tested.
- Do not promote a strategy after a few wins. Strategy promotion requires the External Brain forward gate (minimum independent sessions/sample and no worse risk regime/drawdown).

## Non-negotiable integrity rules
- Do not use post-open information to alter a PREMARKET prediction.
- Do not hide missing data as zero or healthy state.
- Do not suppress CI for prediction-state/code changes that require validation.
- PREMARKET and INTRADAY_EVENT state/decisions are run-type isolated even when stored under a shared append-only ledger root.
- Durable truth lives in GitHub + External Brain + canonical connected sources, not in one conversation's memory.
