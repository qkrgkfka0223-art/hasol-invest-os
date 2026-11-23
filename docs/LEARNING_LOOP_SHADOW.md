# HASOL: evidence-first learning-loop shadow (not Production)

## Objective
Prevent the repeated observed failures from being silently reinterpreted as success. The only Production objective remains highest relative 5-US-regular-session +10% TOUCH candidates Top20 / Top5. This audit **never** mutates prior Frozen, ranks, decision facts, observed price anchors or source timestamps.

## Three evidence-first tests
1. **Memory & issuer coverage:** On a preserved as-of query, retrieve the exact original issuer/SEC source with verified publication timestamp; compare summary-only retrieval with summary plus raw source search on the **same** historical questions. Label source absent from memory vs recorded but retrieval-missed separately. Source breadth verification is external; not supplied by this script.
2. **Point-in-time forecast replay:** Build `HASOL-LEARNING-AUDIT-v1` from **actual** Brain Frozen, source evidence, and timestamped first five completed regular-session daily OHLC. Reject any result from after last completed session; report S1 through S4 as interim, S5 only when all 20x5 original-anchored results are available. For ATR20, record original same-cutoff baseline for **all** selected and shadow-only candidates; do not compare hit rates using different anchors. Full PIT eligible market roster is required to claim market-wide winner recall.
3. **First known failure attribution:** Known material original issuer event published before Frozen and FULL original verified: ticker absent from discovery => `DISCOVERY_FAIL`; ticker present but event release ID missing from its actual captured packet => `CATALYST / DRIVER_ERROR`. Keep `retrospective_discovery=true` if release collected only after Frozen. Do not rewrite past source packets or attribute an unverified event. A modeled rank miss, regime error, or outcome variance remains **UNKNOWN/hypothesis** absent sufficient independent proof.

## Run
```bash
python -m pytest -q tests/test_learning_loop.py
python -m scripts.audit_learning_loop --input /path/to/captured_v1.json --output /path/to/report.json
```

### Input evidence contract
A source system/authorized operator produces a JSON object with:
- `schema`: `HASOL-LEARNING-AUDIT-v1`, `run_id`, `freeze_at_utc`, `blind_locked_at_utc`, `audit_asof_utc`, `last_completed_regular_session`.
- `five_regular_sessions`: exactly five chronological exchange-verified session dates; never ordinary calendar days.
- `frozen`: **exactly 20** original immutable tickers, run_id, rank, original baseline price + observed UTC, matching original Outcome price/hash, LOCKED.
- `candidate_packets`: original pre-frozen ticker and `handled_release_ids` (never reconstituted with hindsight), official rank.
- `issuer_releases`: dated source IDs with published and collected UTC, `material` boolean, and `primary_full_text_verified`; a late collected event cannot retroactively change the original packet.
- `daily_bars`: ticker, completed session date, regular high, regular close. Full S5 requires 20x5 with no gap.
- `atr_shadow`: same evaluated frontier, ranks 1..N, original same-cutoff baseline with observed UTC. A missing nonselected baseline prevents a fair model-vs-shadow outcome comparison.
- Independent proof flags: `source_feed_coverage_verified`, `full_pit_eligible_roster_verified`, `security_eligibility_verified`.

The script is **offline, read-only, deterministic** and can only audit the provided evidence. GitHub Actions synthetic success is not evidence of a live secured Google/issuer/market connector or a clean RUN. A report with incomplete coverage remains `SHADOW_PARTIAL_NOT_CLEAN`. Even with full evidence, it says `SHADOW_EVIDENCE_READY_NOT_PRODUCTION`. There is no automatic factor adjustment, memory rewrite, or Production promotion.

## Acceptance / disconfirmation
- Run a frozen set of historical source-retrieval questions on same-cutoff knowledge, score *source present*, *retrieved*, and *correctly factored into thesis* independently; report baseline vs hybrid recall with denominator and CI. Data needed to compute a live memory metric remains not yet wired.
- Repeated prospective matched cohorts: same market session, same eligible candidates, original captured baselines, full 5D high-touch outcomes; record Model vs ATR20 and market eligible top-winner survival, without post hoc renumbering.
- Rule hypothesis `TESTING -> SUPPORTED` only after independent clean forward cohorts show lower first-failure rates and better Top5 hit/winner survival against the simple baseline. A single CAPR/SLS/CLRO success or price drawdown does not prove rule improvement.
- First disconfirming evidence: original source unavailable as-of despite claimed completeness; release timestamp later than frozen; original baseline mismatch; omitted markets; missing original price anchor; or production benefit failing prospectively.
