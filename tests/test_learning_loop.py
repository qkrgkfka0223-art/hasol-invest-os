"""Regression tests: issuer omission, time travel, same-anchor comparisons and error attribution."""
from copy import deepcopy

from scripts.audit_learning_loop import audit


DATES = ["2026-11-19", "2026-11-20", "2026-11-23", "2026-11-24", "2026-11-25"]
RUN = "RUN-20261119-FAST10-LEAN-PREOPEN-001"


def fixture(last="2026-11-20"):
    fs = []
    candidates = []
    bars = []
    shadow = []
    for i in range(20):
        t = f"T{i:02d}"
        base = float(10 + i)
        fs.append({
            "ticker": t, "run_id": RUN, "rank": str(i+1),
            "baseline_price": base, "baseline_observed_at_utc": "2026-11-19T13:17:00Z",
            "outcome_baseline_price": base, "row_hash": f"HASH-{i}",
            "outcome_row_hash": f"HASH-{i}", "lock": "LOCKED",
        })
        candidates.append({"ticker": t, "official_rank": i+1, "handled_release_ids": []})
        shadow.append({
            "ticker": t, "rank": str(i+1), "baseline_price": base,
            "baseline_observed_at_utc": "2026-11-19T13:17:00Z",
        })
        for d in DATES:
            if d <= last:
                high = 11.1 * (base / 10) if (i == 0 and d == DATES[0]) else base * 1.02
                if i == 6 and d == DATES[1]:
                    high = base * 1.12
                bars.append({"ticker": t, "session_date": d, "regular_high": high,
                             "regular_close": base * 0.98})
    return {
        "schema": "HASOL-LEARNING-AUDIT-v1",
        "run_id": RUN, "freeze_at_utc": "2026-11-19T13:18:10Z",
        "blind_locked_at_utc": "2026-11-19T13:00:00Z",
        "audit_asof_utc": "2026-11-23T00:00:00Z",
        "last_completed_regular_session": last,
        "five_regular_sessions": DATES,
        "frozen": fs, "candidate_packets": candidates,
        "atr_shadow": shadow, "daily_bars": bars,
        "issuer_releases": [], "source_feed_coverage_verified": False,
        "full_pit_eligible_roster_verified": False, "security_eligibility_verified": False,
    }


def test_interim_counts_not_confused_with_final():
    z = audit(fixture())
    assert z["maturity"] == "S2_INTERIM"
    assert z["top20_cumulative_hit10"] == 2
    assert z["top5_cumulative_hit10"] == 1
    assert z["day1_top20_hit10"] == 1
    assert z["model_vs_atr_outperformance"] == "UNKNOWN"
    assert z["promotion"].startswith("DORMANT_SHADOW")
    assert z["original_frozen_mutated"] is False


def test_future_session_bars_block():
    x = fixture()
    x["daily_bars"].append({"ticker": "T00", "session_date": "2026-11-23",
                             "regular_high": 999, "regular_close": 20})
    assert audit(x)["decision"] == "BLOCK"


def test_stale_quote_downgrades_not_rewrites():
    x = fixture()
    x["frozen"][2]["baseline_observed_at_utc"] = "2026-11-19T13:01:00Z"
    a = audit(x)
    assert a["decision"] == "SHADOW_PARTIAL_NOT_CLEAN"
    assert "T02" in a["stale_quote_tickers"]


def test_tampered_original_baseline_blocks():
    x = fixture()
    x["frozen"][0]["outcome_baseline_price"] = 123
    assert audit(x)["decision"] == "BLOCK"


def test_missing_issuer_material_release_identifies_catalyst_stage():
    x = fixture()
    x["issuer_releases"] = [{
        "ticker": "T06", "release_id": "T06-8K-REAL", "material": True,
        "published_at_utc": "2026-11-19T12:00:00Z",
        "collected_at_utc": "2026-11-22T12:00:00Z",
        "primary_full_text_verified": True,
    }]
    x["candidate_packets"][6]["handled_release_ids"] = []
    z = audit(x)
    assert z["first_known_failure"] == "CATALYST / DRIVER_ERROR"
    assert z["documented_failure_events"][0]["retrospective_discovery"] is True


def test_missing_candidate_is_discovery_failure():
    x = fixture()
    x["candidate_packets"] = [r for r in x["candidate_packets"] if r["ticker"] != "T06"]
    x["issuer_releases"] = [{
        "ticker": "T06", "release_id": "RELEASE", "material": True,
        "published_at_utc": "2026-11-19T12:00:00Z",
        "collected_at_utc": "2026-11-19T13:10:00Z",
        "primary_full_text_verified": True,
    }]
    z = audit(x)
    assert z["first_known_failure"] == "DISCOVERY_FAIL"


def test_after_freeze_release_cannot_be_backdated():
    x = fixture()
    x["issuer_releases"] = [{
        "ticker": "T06", "release_id": "POST", "material": True,
        "published_at_utc": "2026-11-19T14:00:00Z",
        "collected_at_utc": "2026-11-20T00:00:00Z",
        "primary_full_text_verified": True,
    }]
    z = audit(x)
    assert z["first_known_failure"] == "UNKNOWN"
    assert z["documented_failure_events"] == []


def test_source_without_original_verified_cannot_be_attributed():
    x = fixture()
    x["issuer_releases"] = [{
        "ticker": "T06", "release_id": "UNVERIFIED", "material": True,
        "published_at_utc": "2026-11-19T12:00:00Z",
        "collected_at_utc": "2026-11-20T12:00:00Z",
        "primary_full_text_verified": False,
    }]
    z = audit(x)
    assert z["first_known_failure"] == "UNKNOWN"
    assert any("not verified" in v for v in z["gaps"])


def test_missing_bars_never_counted_as_matured_final():
    x = fixture(last="2026-11-25")
    x["audit_asof_utc"] = "2026-11-26T00:00:00Z"
    x["daily_bars"] = [b for b in x["daily_bars"] if b["ticker"] != "T10" or b["session_date"] != "2026-11-25"]
    z = audit(x)
    assert z["maturity"] == "S5_MATURED"
    assert z["decision"] == "SHADOW_PARTIAL_NOT_CLEAN"
    assert any("not fully matured or complete" in v for v in z["gaps"])


def test_missing_shadow_anchors_cannot_claim_outperformance():
    x = fixture()
    x["atr_shadow"][0]["baseline_observed_at_utc"] = "2026-11-19T12:00:00Z"
    z = audit(x)
    assert any("same-cutoff baseline" in v for v in z["gaps"])
    assert z["model_vs_atr_outperformance"] == "UNKNOWN"


def test_shadow_frozen_price_mismatch_blocks():
    x = fixture()
    x["atr_shadow"][2]["baseline_price"] += 1
    assert audit(x)["decision"] == "BLOCK"


def test_duplicated_bar_blocks():
    x = fixture()
    x["daily_bars"].append(deepcopy(x["daily_bars"][0]))
    assert audit(x)["decision"] == "BLOCK"


def test_rank_integrity_blocks():
    x = fixture()
    x["frozen"][8]["rank"] = "1"
    assert audit(x)["decision"] == "BLOCK"


def test_partial_audit_never_promotes_on_outcome_even_when_hits():
    x = fixture(last="2026-11-25")
    x["audit_asof_utc"] = "2026-11-26T00:00:00Z"
    z = audit(x)
    assert z["maturity"] == "S5_MATURED"
    assert z["promotion"].startswith("DORMANT_SHADOW")
    assert z["full_market_winner_recall"] == "UNKNOWN"
