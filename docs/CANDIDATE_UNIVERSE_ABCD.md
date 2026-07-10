# HASOL A/B/C/D Candidate Universe

This document defines the operating universe for HASOL after v1.5.

## Purpose

HASOL no longer treats every US-listed mover as an execution candidate.

- A/B groups are prediction and event-detection groups.
- C group is review-only mover learning.
- D group is execution-banned risk.

## Groups

### A: Prediction Watchlist

A names are liquid or semi-liquid stocks on strong market axes.

Examples:
- AI infrastructure
- Datacenter power
- Nuclear / power grid
- Defense / space
- Semiconductor follow-through
- Earnings surprise growth stocks

A names may become execution candidates after market, event, price-structure, liquidity, and web-validation checks.

### B: Event Watchlist

B names are event-first candidates.

Examples:
- FDA / clinical
- 8-K
- Form 4
- 13D / 13G
- M&A
- major contract
- earnings / guidance raise

B names are conditional execution candidates only after the event thesis is validated and price is still early.

### C: Review-Only Movers

C names are kept for learning.

They may appear in daily mover reports and missed-mover reviews, but they cannot become execution candidates.

### D: Execution-Banned

D names are automatically locked.

Examples:
- likely reverse split / corporate action anomaly
- warrant / preferred / unit-like securities
- delisting / dilution / offering risk
- ultra-low price and poor liquidity
- extreme post-spike names

D names are never execution candidates.

## Required CSV Columns

`data/candidate_universe.csv` must contain:

- ticker
- group
- axis
- event_type
- watch_reason
- liquidity_bucket
- risk_bucket
- execution_allowed

## Execution Rule

`execution_candidates.csv` can only contain A/B names with `execution_allowed` equal to `yes` or `conditional`.

C/D names can still appear in raw/scored/top20/top5 for learning, but must remain locked out of execution.

## Current Status

This is not a buy list. It is the operating universe for the detector.

Final execution still requires:

- market GO or SOFT_GO
- event thesis
- price earlyness
- support/invalid line
- volume not overheated
- web validation
- manual approval
