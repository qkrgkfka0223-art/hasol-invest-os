# HASOL Production Blockers

Current status: `NOT_PRODUCTION`.

Resolved on 2026-08-25:

- Full-Market Quant Engine v1 code build
- Quant CI / deterministic tests
- point-in-time broad reference artifact + SHA256
- historical consolidated SIP full-market scale test (98.718% coverage)
- literal `NA` ticker parsing bug
- special preferred-style symbol contamination
- invalid-symbol batch blast-radius handling

Open blockers, in order:

1. Final universe security-type purity: deterministic COMMON_STOCK eligibility.
2. Web Event Detector full-market event-first scale E2E: source -> ticker mapping -> dedupe -> primary evidence lineage.
3. Canonical analyst expectations/revision source with as-of snapshots.
4. 09:25 ET premarket data freshness and coverage gate.
5. HASOL Fusion -> Top20/Top5 -> 09:25 freeze -> External Brain readback.
6. Three clean timed E2E cycles, restore test, intraday trigger path, forward review gates.

Operational credential blocker:

- GitHub Actions repository secrets `ALPACA_API_KEY_ID` and `ALPACA_API_SECRET_KEY` must be configured before unattended full-market SIP Quant can execute in GitHub.

Credentials must not be committed to the repository, artifacts, Sheets, or chat logs.
