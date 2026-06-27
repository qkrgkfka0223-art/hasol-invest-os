# Current Status

Last updated: 2026-06-27 KST

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
version: HASOL_DETECTOR_V1.2
mode status: sample/live separated
execution candidates: locked by default
web validation: required
sheet auto-write: not enabled
```

## Good structure confirmed

- market_cap added
- cap_bucket added
- Top20 cap-bucket quota added
- sample output locked
- live output requires web validation
- data_quality_status added
- run_metadata.json added

## Known limitations

- yfinance live data stability not yet proven
- SEC live scanner is still a hook, not full production scanner
- news source validation is manual/web-assisted
- market judgment remains externally supplied by HASOL
- no Google Sheet write automation yet

## Next versions

```text
v1.3 = Top20 web validation helper
v1.4 = SEC live scanner expansion
v1.5 = market judgment module
v2.0 = Sheet write integration after stability
```

## Hard rule

Do not treat sample Top5 as execution candidates.
