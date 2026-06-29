# Current Status

Last updated: 2026-06-29 KST

## Repository role

`hasol-invest-os` is the GitHub detection engine repository.

It is not the external brain and it is not a trading recommendation engine.

```text
GitHub/code = detection
Sheet = memory/external brain
HASOL = judgment/compression
Web = validation evidence
User = final approval
```

## Active baseline

```text
version: HASOL_DETECTOR_V1.3
mode status: sample/live separated
execution candidates: locked by default
web validation: required
sheet auto-write: not enabled
```

## v1.3 added after recent spike review

- SEC_CLUSTER detection
- Form 3 / Form 4 / 13D / 13G / 8-K cluster awareness
- micro/nano detect-only mode
- famous partner keywords: Starlink, SpaceX, NASA, AMD, NVIDIA, DoD, FDA
- biotech expansion keywords: BLA accepted, resubmitted BLA, late-stage trial, primary endpoint, exclusive rights, licensing deal
- post_spike_stage classifier
- stronger web_validation_checklist.csv
- web_review_helper.py

## Good structure confirmed

- market_cap added
- cap_bucket added
- Top20 cap-bucket quota added
- sample output locked
- live output requires web validation
- data_quality_status added
- run_metadata.json added
- Top20 review helper added

## Known limitations

- yfinance live data stability not yet proven
- SEC live scanner is still a hook, not full production scanner
- news source validation is manual/web-assisted
- market judgment remains externally supplied by HASOL
- no Google Sheet write automation yet

## Next versions

```text
v1.4 = SEC live scanner expansion
v1.5 = market judgment module
v2.0 = Sheet write integration after stability
```

## Hard rule

Do not treat sample Top5 as execution candidates.

Do not treat micro/nano detection as executable without web review and user approval.
