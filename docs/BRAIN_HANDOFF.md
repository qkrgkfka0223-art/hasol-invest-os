# HASOL Brain → GitHub deterministic handoff (audit only)

## Purpose

A narrow, testable gate between the **one official current Brain**
(HASOL_EXTERNAL_BRAIN / Google Sheets) and GitHub compute. This is an **offline
validator**, not an autonomous task runner or an order executor. It never edits
FROZEN, OUTCOMES, or any Sheet. It does not fetch prices or issuer publications.

* **BLOCK**: inconsistent Top20/Top5, run IDs, ranks, Frozen/Outcome baseline
  parity, lock, or definitively invalid selected-security eligibility.
  **Do not commit a new official Frozen**.
* **OFFICIAL_PARTIAL_NOT_CLEAN**: valid basic record but a primary-issuer,
  price-blind timing, quote-age, point-in-time market roster, or shadow
  integrity gap. If a defensible official selection exists, retain its
  degraded label; **never count it as CLEAN**.
* **EVIDENCE_READY_REQUIRES_INDEPENDENT_VERIFY**: the supplied JSON internally
  meets all gates. This is **not a CLEAN certification**: source URL, issuer
  release time, market feed, ticker security type, complete PIT universe and
  immutable Sheet readback still require actual verification using connected
  apps. Code cannot authenticate user-supplied assertions.

Historical Frozen must never be changed or retrospectively "fixed".

## Run

1. An authorized orchestrator reads the **actual seven Brain tabs** and current
   ACTIVE policy. Complete source collection and durable issuer-first Blind
   write/readback **before** any price/reaction tool call on the new RUN.
2. Only **after** durable blind lock, use connected Alpaca/TickerLayer tools for
   selected-security, timestamped quotes, previous 21 completed regular bars,
   market-calendar and eligible roster. Do not infer completeness from active
   exchange listings. Preserve all original observed-at timestamps.
3. Export one RUN's exact named-column rows as a private JSON file with fields
   shown below, **not** committed to a public GitHub repository.
4. Run:
   \`python -m scripts.validate_brain_handoff --input /private/hasol_run.json --output /private/qa.json\`
   For promotion tests, append \`--require-evidence-ready\` (exit 2 = BLOCK,
   exit 3 = partial, exit 0 = internally consistent).
5. Independently read back the frozen destination after the 20/5/20 commit;
   compare IDs, hashes, prices, timestamps, and source provenance. Keep source
   snapshots and a content digest outside public GitHub in access-controlled
   storage. Existing Google Sheets remains the official immutable record.
6. Compare official Top5 vs pre-Frozen same-frontier SIMPLE_ATR20_V1 only after
   five full regular sessions. Missing data means UNSCORABLE, not zero.

## Input contract

JSON root: \`schema=HASOL-BRAIN-HANDOFF-v1\`, \`run_id\`,
\`blind_locked_at_utc\`, \`first_market_data_access_at_utc\`,
\`predictions\`, \`frozen\`, \`outcomes\`, \`universe\`, and \`shadow\`.

* \`predictions\`: from \`02_PREDICTIONS\`, keyed by \`TICKER_SNAPSHOT\`; copy
  \`RUN_ID\`, \`OFFICIAL_MODEL_RANK\`, \`MODEL_TOP20\`, \`TOP5\`,
  \`DISCOVERY_CLASS\`, \`BLIND_PACKET_AT_UTC\`,
  \`BLIND_FACTS_SUMMARY\`, \`BLIND_JUDGMENT\`, and \`SOURCE_REF\`.
  Add **separately checked** \`ISSUER_RELEASED_AT_UTC\` from actual publisher
  content (not \`COLLECTED_AT_UTC\`) and
  \`source_independently_verified\` Boolean. Price first encountered cannot be
  earlier than durable blind lock.
* \`frozen\`: the exact \`03_FROZEN\` original \`RUN_ID\`,
  \`TICKER_SNAPSHOT\`, \`RANK\`, \`TOP5\`, \`BASELINE_PRICE\`,
  \`BASELINE_OBSERVED_AT_UTC\`, \`FROZEN_AT_UTC\`, \`LOCK\`,
  \`PRICE_SOURCE\`. Augment each selected row with independently verified
  \`eligibility={exchange,security_type,listed_sessions,price,adtv20_usd}\`.
  Common stock requires major exchange, 20 sessions, price >=$3 and 20-day
  average dollar volume >=$10M. Do not replace missing values with guesses.
* \`outcomes\`: from \`04_OUTCOMES\`, original \`RUN_ID\`, \`TICKER_SNAPSHOT\`,
  \`RANK\` and \`BASELINE_PRICE\`. Must exactly match Frozen.
* \`universe={complete,snapshot_sha256,asof_utc,independently_verified}\`.
  Only a **real same-cutoff full eligible market roster** can set complete and
  independently_verified True. Separate NYSE/NASDAQ/AMEX active metadata is
  not sufficient.
* \`shadow={method:"SIMPLE_ATR20_V1",status:"SCORABLE",scored_at_utc,scores}\`,
  where scores contain {ticker,score,rank} across the same evaluated frontier.
  The validator checks deterministic score order and pre-Frozen as-of, not
  whether input scores were computed from correct actual OHLC bars.
  If not independently scored on time, use \`status:"UNSCORABLE"\`.

## Coverage / limits

This patch has **synthetic unit regression tests**, not a successful live
production E2E. It does not introduce Alpaca API credentials into GitHub or
pretend that the ChatGPT connected Alpaca account authorizes GitHub Actions.
The existing \`run_full_market_quant.py\` is deprecated and the current
\`run_web_candidate_quant.py\` uses Yahoo/yfinance for **detection only**.
Neither is itself a full-market, issuer-blind, clean execution pipeline.

GitHub Actions here runs *only* synthetic checks without credentials.
For unattended daily ingestion and automatic Sheet writes, a subsequent
separately reviewed integration needs authenticated data access and Google
service permissions; keep credentials only in GitHub Actions secrets or
another suitable secret manager, never in source, Sheets, artifact, or chat.
