# HASOL clean A/B/C trial — experimental, NOT production

Goal: test whether the independently prepared HASOL AI Top20/Top5 adds five-regular-session +10% high-touch value over (A) price/volume baseline and (B) issuer-event baseline. Every method uses the same original eligible cohort, cutoff, stock-specific baseline and five-session outcomes.

This prototype does not modify HASOL_EXTERNAL_BRAIN, execute a broker order, require an Alpaca key, or claim a verified prediction. All results declare clean_forward_credit = false.

## Stage boundaries

Stage 1 (lock): the command accepts ONLY an issuer JSON file. It rejects unknown fields and share-price/reaction phrases, requires a source URL and known-at timestamp for each issuer fact, and creates separate blind and manifest files with SHA-256 using no-overwrite writes. It does not accept a market/model input.

Stage 2 (freeze): first checks the Blind file hash and exact run ID/cutoff. It then accepts SIP market data (at most 15 minutes old at the preopen cutoff) and an AI ranking. Exchange, common-stock/direct-ordinary type, non-SPAC, at least $3, at least 20 listed sessions and 20-day average traded value >= $10 million are enforced. The AI rank must cover EXACTLY the same eligible pool. Rejects freeze once the 09:30 ET regular session opens because daily S1 high would be unsafe for intraday entry. Creates one frozen file using no-overwrite writes.

Stage 3 (review): checks immutable Frozen digest. After exactly five completed US regular sessions, evaluates each eligible ticker's daily high against 1.10 times its original Frozen price, and separately computes last close return. Scores each A/B/C Top20/Top5 and actual winning Top20/Top5 overlap WITHIN THAT COHORT ONLY, not the entire US eligible market.

## Three pre-registered methods

A_SIMPLE: existing-style percentile ranks for 5-session momentum, RVOL20 and ATR20, summed and sorted deterministically.

B_ISSUER_EVENT: issuer-only frozen integer scores 2*novelty + 3*expectation_delta + 2*fundamental_impact; this is an illustrative independent baseline, not calibrated predictive truth.

C_HASOL_AI: externally supplied, independent complete candidate order with thesis and counter. This prototype does not generate, modify or claim to verify the AI's reasoning.

All A/B/C rankings cover the exact eligible cohort BEFORE selecting Top20/Top5. A ranking of an already model-selected 20 is not a fair independent baseline.

## Commands

    python -m hasol_validation.clean_trial lock --issuer issuer.json --out output/trial-001
    python -m hasol_validation.clean_trial freeze --locked output/trial-001 --market market.json --model model.json
    python -m hasol_validation.clean_trial review --frozen output/trial-001/trial_frozen.json --outcomes outcomes.json --out output/trial-001/review.json
    python -m pytest -q tests/test_clean_trial.py

Issuer JSON root fields: run_id, cutoff_utc (ISO 8601 timezone-aware UTC), candidates (20 or more). Each issuer candidate has ticker, security_id, known_at_utc, source_url (https primary evidence), fact (issuer-only text), novelty (integer 0..3), expectation_delta (integer -3..3), fundamental_impact (integer 0..3).

Market JSON root fields: run_id, cutoff_utc, session1_date (ET), candidates. Each candidate has ticker, security_id, last_price, observed_at_utc, adtv20_usd, listing_sessions, security_type (COMMON_STOCK or US_LISTED_ORDINARY), exchange (NASDAQ, NYSE or NYSEAMERICAN), is_spac (boolean), momentum5_pct, relative_volume20, atr20_pct, source (SIP). Exact same ticker set as issuer packet is mandatory.

Model JSON root fields: run_id, cutoff_utc, asof_utc and ranked, which is a complete ordered list of exactly the eligible ticker set. Each ranked element has ticker, thesis and counter. As-of must be after issuer lock and no later than cutoff.

Outcomes JSON root fields: run_id, asof_utc, session_dates (five distinct sorted US trading dates, first is session1_date), rows. Each row has ticker, source (SIP) and bars; each bar has date, high and close. Exactly five actual session bars must be present for each originally eligible candidate.

## Tested failure cases

- Price reaction phrase or market field in issuer-only packet: reject BEFORE issuer lock.
- Blind file changed after locking: fail hash verification.
- Quote older than 15 minutes at cutoff, quote after cutoff, or quote timestamp in future: reject.
- Changed security identifier or incomplete AI ranking: reject.
- Freeze attempted at or after NYSE regular open: reject.
- Invalid future or incomplete S5 outcome data: reject.
- Rewriting Frozen or retrospective: reject.
- Five-day TOUCH vs close-return: report separately.

All tests are synthetic. Passing them does NOT show actual prediction lift, full-market US discovery, credible public-company evidence, or price-Blind AI-context purity.

## Crucial remaining limitation

The code blocks price-bearing INPUT FIELDS at the Blind stage. It CANNOT prevent upstream ChatGPT/web-search workers from having already seen prices and then passing issuer-only JSON. That requires a separately permissioned issuer collector / market collector and independent audit of the first moment any model sees prices. Therefore this experiment cannot earn CLEAN_FORWARD status even if all local tests pass.

The actual full-market rising Top20/Top5 and Discovery-to-Top5 winner survival are UNKNOWN until a complete, same-cutoff point-in-time US eligible roster AND stock-specific at-freeze prices exist. Never substitute hindsight data. Do not alter original Frozen or claim Production improvement.

Next promotion gate: run isolated issuer-first collectors with audited chronology; produce full eligible universe and baseline; carry three methods forward for multiple REAL 5-session completed runs; compare results without fitting on outcomes.
