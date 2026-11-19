# HASOL pre-Frozen source and discovery audit (SHADOW, not production)

## Problem corrected in code

On 2026-11-17 the existing SLS candidate was ranked #21 despite a new issuer
Phase 3 release published at 07:00 ET (12:00 UTC), before the 08:02 ET Frozen
cutoff. Using an older 2026-11-12 packet produced a materially outdated
judgment. The observed same-day close increase is an *ex-post* benchmark, not
proof of 5-session +10% model lift.

`scripts/audit_discovery_freshness.py` now checks the source evidence made
available to an orchestrator before committing any *new* Frozen. It cannot
discover missing publications itself or prove feeds are complete.

## Minimal execution contract

1. Restore ACTIVE control and the seven real Brain tabs. Finish due Reviews.
2. From *original issuer/SEC source only*, collect releases with
   `published_at_utc` and independent `collected_at_utc`. No preview of
   prices or reactions. Persist candidate evidence and Price-Blind readback.
3. Re-query issuer-primary release indexes immediately before the proposed
   freeze; do not silently keep yesterday's issuer packet. Record full sweep
   timestamps and whether coverage was independently verified.
4. Assemble a **private** JSON snapshot from the same run, with
   `schema: HASOL-PREFREEZE-v1`, target `run_market_date`,
   `last_completed_regular_session`, `blind_locked_at_utc`,
   `first_price_exposure_at_utc`, `cutoff_utc`, and arrays:
   `candidate_packets`, `issuer_releases`, `issuer_sweeps`,
   `lagged_leader_batches`, `live_mover_snapshots`.
   Include `shadow_discovery_tickers`,
   `full_pit_eligible_roster_verified`, and
   `release_feed_completeness_independently_confirmed`.
5. Run `python -m scripts.audit_discovery_freshness --input /private/run.json
   --require-evidence-ready`. Exit **2** = known material release missed,
   invalid timestamps or look-ahead → BLOCK new Frozen until addressed.
   Exit **3** = incomplete proof, stale sweep, price exposure, insufficient
   PIT coverage or incomplete lagged-shadow intake → NOT CLEAN.
   Exit **0** = internally consistent *only*; independent real-time source
   authentication and persistence still required.
6. Only then use the *existing* `validate_brain_handoff.py` for same-run
   eligibility (common listed20/price3/ADTV20 $10m), fresh observed trade,
   20/5/20 parity, unique ranks, independent ATR20 shadow, and immutable
   write/readback. Both tests must be used; neither establishes prediction
   edge or replaces the official S0-S7 run procedure.

## SLS-style blocking condition

If a material SLS release is observed at 12:00 UTC and the pre-Frozen
candidate packet cites only the prior release, the latest
`release_id` is absent from `handled_release_ids`.
The gate returns `MATERIAL_ISSUER_RELEASE_NOT_HANDLED` and BLOCK.

A large upward move is *not* proof the catalyst was knowable, nor may
future-day winners be added retroactively. A source release occurring after
the original Price-Blind lock is tagged as nonclean even if handled later.

## Discovery expansion is SHADOW

- Record prior completed 1-day/3-session daily Top100 as timestamped,
  backward-only lists and merge with shadow candidates after Blind lock.
- Record live premarket/intraday movers separately as
  `AFTER_PRICE_DISCOVERY`, never claim price-blind issuer origin.
- Pass all current eligibility gates before ranking. Movers are not
  automatically put into the official Top20.
- Compare matched-run (a) discovered actual eligible 5D +10% winners,
  (b) Top20/Top5 official 5D +10 touch from original Frozen price,
  (c) official vs pre-frozen SIMPLE_ATR20_V1. Historical same-day Top100
  overlap is a *different* metric and cannot certify improved forecasts.

## Honest limits

All regression tests are synthetic and live-data independent. A complete
issuer release feed and historical point-in-time universe are not guaranteed
by code. The current canonical Brain and original Frozen are not changed by
this branch. Until an authenticated orchestrator supplies real snapshots,
calls both gates before commit, and independently reads back the result,
status is **CODE_TESTED / LIVE_E2E_UNPROVEN / PRODUCTION_UNCHANGED**.
No scheduled automation reliability is implied by a successful CI build.
