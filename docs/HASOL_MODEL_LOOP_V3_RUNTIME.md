# HASOL Model Loop v3 Runtime

This module is the fail-closed runtime contract for official HASOL predictions.

## Non-negotiable behavior

1. Broken or incomplete data NEVER becomes `VALID_NO_CANDIDATE`.
2. Before External Brain write/readback, a run can only reach `PREDICTION_WRITE_READY`.
3. `VALID_PREDICTION` is emitted only after the independently read-back prediction hash matches the frozen hash.
4. Prediction and Execution are separate. Runtime defaults execution to `NOT_EVALUATED` and never invents a trade.
5. Same frozen input must produce the same universe hash, prediction hash, Top20 and Top5.
6. Future evidence relative to the 16:00 ET cutoff invalidates the run.

## Current official structural contract

- Exchanges: Nasdaq / NYSE / NYSE American
- Security: primary-listed common stock only
- Close >= $3
- ADV20 >= $10M
- At least 20 completed sessions
- Market-data coverage >= 98%
- Six positive engines:
  - earnings_expectations
  - future_flow_event
  - price_rs
  - supply_demand
  - quality
  - market_regime
- Aggregate: median of valid frozen-universe percentiles minus risk penalty
- Minimum valid engines: 4/6
- Top20 tie-break: Future Flow/Event -> Earnings/Expectations -> ADV20 -> ticker
- Top5 compression: median of six anchored components using only 0/25/50/75/100

## State machine

`BOOT -> RESTORE -> DATA_HEALTH -> MARKET_REGIME -> UNIVERSE_FREEZE -> DETECT -> EVIDENCE -> THESIS -> CHALLENGE -> RANK -> COMPRESSION -> EXECUTION -> PREDICTION_FREEZE -> WRITE_READY -> CLOSED`

Any mandatory gate failure moves to `INVALID`.

## Important boundary

This runtime enforces the loop and ranking contract but does not yet claim that all six upstream raw-engine formulas are fully sourced from live point-in-time feeds. Those upstream detectors must populate `engine_raw`, evidence, thesis, counter-thesis and compression anchors without future leakage. Until that bridge is connected and External Brain readback succeeds, the system is not Production.
