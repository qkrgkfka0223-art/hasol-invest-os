from __future__ import annotations

import copy
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from hasol_validation import clean_trial as trial


def _write(path: Path, obj: dict) -> Path:
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return path


def _inputs(tmp_path: Path):
    cutoff = datetime(2099, 2, 18, 9, 25, tzinfo=ZoneInfo("America/New_York"))
    while cutoff.weekday() >= 5:
        cutoff += timedelta(days=1)
    utc_cutoff = cutoff.astimezone(timezone.utc)
    cutoff_iso = utc_cutoff.isoformat()
    tickers = [f"T{i:03d}" for i in range(25)]
    issuer = {
        "run_id": "TEST-SAME-CUTOFF-001", "cutoff_utc": cutoff_iso,
        "candidates": [
            {
                "ticker": t, "security_id": f"HSID:{i:06d}",
                "known_at_utc": (utc_cutoff - timedelta(days=1)).isoformat(),
                "source_url": f"https://investor.example.com/{t}/filing",
                "fact": f"Company {t} reported quarterly revenue and updated operating guidance.",
                "novelty": i % 4,
                "expectation_delta": (i % 7) - 3,
                "fundamental_impact": i % 4,
            }
            for i, t in enumerate(tickers)
        ],
    }
    market = {
        "run_id": issuer["run_id"], "cutoff_utc": cutoff_iso,
        "session1_date": cutoff.date().isoformat(),
        "candidates": [
            {
                "ticker": t, "security_id": f"HSID:{i:06d}",
                "last_price": float(10 + i),
                "observed_at_utc": (utc_cutoff - timedelta(minutes=2)).isoformat(),
                "adtv20_usd": float(15_000_000 + i * 1_000_000),
                "listing_sessions": 100,
                "security_type": "COMMON_STOCK", "exchange": "NASDAQ",
                "is_spac": False, "momentum5_pct": float(i - 15),
                "relative_volume20": 1.0 + i / 20.0,
                "atr20_pct": 2.0 + (i % 7),
                "source": "SIP",
            }
            for i, t in enumerate(tickers)
        ],
    }
    model = {
        "run_id": issuer["run_id"], "cutoff_utc": cutoff_iso,
        "asof_utc": (utc_cutoff - timedelta(minutes=1)).isoformat(),
        "ranked": [
            {"ticker": t, "thesis": f"New demand may develop for {t}.",
             "counter": f"Existing expectations may fully price {t}."}
            for t in reversed(tickers)
        ],
    }
    return utc_cutoff, issuer, market, model


def _lock(tmp_path, monkeypatch):
    cutoff, issuer, market, model = _inputs(tmp_path)
    source = _write(tmp_path / "issuer.json", issuer)
    locked = tmp_path / "lock"
    monkeypatch.setattr(trial, "_now", lambda: cutoff - timedelta(minutes=25))
    manifest = trial.lock_issuer(source, locked)
    return cutoff, manifest, market, model, locked


def _freeze(tmp_path, monkeypatch):
    cutoff, manifest, market, model, locked = _lock(tmp_path, monkeypatch)
    market_path = _write(tmp_path / "market.json", market)
    model_path = _write(tmp_path / "model.json", model)
    monkeypatch.setattr(trial, "_now", lambda: cutoff + timedelta(minutes=1))
    frozen = trial.freeze(locked, market_path, model_path)
    return cutoff, manifest, market, model, locked, frozen


def test_all_three_methods_same_eligible_pool_cutoff_and_baseline(tmp_path, monkeypatch):
    cutoff, manifest, market, model, locked, result = _freeze(tmp_path, monkeypatch)
    data = result["payload"]
    assert data["candidate_n"] == data["eligible_n"] == 25
    assert data["status"] == "EXPERIMENT_ONLY"
    assert data["clean_forward_credit"] is False
    assert len(data["baseline"]) == 25
    for p in data["portfolios"].values():
        assert len(p["ranks"]) == len(set(p["ranks"])) == 25
        assert len(p["top20"]) == 20
        assert len(p["top5"]) == 5
        assert set(p["ranks"]) == set(data["baseline"])
    assert data["portfolios"]["C_HASOL_AI"]["top5"] == ["T024", "T023", "T022", "T021", "T020"]
    assert trial._blind_read(locked)[1] == manifest
    with pytest.raises(trial.TrialError, match="immutable"):
        trial.freeze(locked, tmp_path / "market.json", tmp_path / "model.json")
    with pytest.raises(TrialErrorOrFileExists):
        trial.lock_issuer(tmp_path / "issuer.json", locked)


# Python's immutable-file write protection raises either the explicit gate error
# or the OS-level exclusive-file exception depending on the entry point.
TrialErrorOrFileExists = (trial.TrialError, FileExistsError)


@pytest.mark.parametrize("contamination", [
    {"fact": "Q3 revenue rose; stock price jumped 22 percent in premarket trading."},
    {"last_price": 52.4},
    {"fact": "Q3 surprise. 주가 급등 after earnings."},
])
def test_price_reaction_or_market_field_blocked_before_blind_lock(tmp_path, monkeypatch, contamination):
    cutoff, issuer, _, _ = _inputs(tmp_path)
    issuer["candidates"][0].update(contamination)
    source = _write(tmp_path / "issuer.json", issuer)
    monkeypatch.setattr(trial, "_now", lambda: cutoff - timedelta(minutes=25))
    with pytest.raises(trial.TrialError):
        trial.lock_issuer(source, tmp_path / "lock")
    assert not (tmp_path / "lock" / "blind.json").exists()


def test_tampered_issuer_lock_never_enters_market_stage(tmp_path, monkeypatch):
    cutoff, _, market, model, locked = _lock(tmp_path, monkeypatch)
    p = locked / "blind.json"
    p.write_text(p.read_text().replace("operating guidance", "speculative guidance"))
    monkeypatch.setattr(trial, "_now", lambda: cutoff + timedelta(minutes=1))
    with pytest.raises(trial.TrialError, match="tampered"):
        trial.freeze(locked, _write(tmp_path / "market.json", market),
                     _write(tmp_path / "model.json", model))


def test_reject_future_or_aging_quote_and_security_id_swap(tmp_path, monkeypatch):
    cutoff, _, market, model, locked = _lock(tmp_path, monkeypatch)
    monkeypatch.setattr(trial, "_now", lambda: cutoff + timedelta(minutes=1))
    for key, value in [
        ("observed_at_utc", (cutoff + timedelta(minutes=2)).isoformat()),
        ("observed_at_utc", (cutoff - timedelta(minutes=30)).isoformat()),
        ("security_id", "HSID:DIFFERENT"),
    ]:
        variant = copy.deepcopy(market)
        variant["candidates"][0][key] = value
        with pytest.raises(trial.TrialError):
            trial.freeze(locked, _write(tmp_path / f"market-{key}-{value[:8]}.json", variant),
                         _write(tmp_path / "model.json", model))
    assert not (locked / "trial_frozen.json").exists()


def test_reject_ai_rank_missing_and_post_open_freeze(tmp_path, monkeypatch):
    cutoff, _, market, model, locked = _lock(tmp_path, monkeypatch)
    x = copy.deepcopy(model)
    x["ranked"].pop()
    monkeypatch.setattr(trial, "_now", lambda: cutoff + timedelta(minutes=1))
    with pytest.raises(trial.TrialError, match="EXACT SAME"):
        trial.freeze(locked, _write(tmp_path / "market.json", market),
                     _write(tmp_path / "bad-model.json", x))
    monkeypatch.setattr(trial, "_now", lambda: cutoff + timedelta(minutes=6))
    with pytest.raises(trial.TrialError, match="session opened"):
        trial.freeze(locked, tmp_path / "market.json",
                     _write(tmp_path / "model.json", model))


def _five_sessions(start: str) -> list[str]:
    day = date.fromisoformat(start)
    sessions = []
    while len(sessions) < 5:
        if day.weekday() < 5:
            sessions.append(day.isoformat())
        day += timedelta(days=1)
    return sessions


def _outcomes(frozen: dict) -> dict:
    packet = frozen["payload"]
    dates = _five_sessions(packet["session1_date"])
    rows = []
    for i, (ticker, info) in enumerate(sorted(packet["baseline"].items())):
        price = info["price"]
        bars = []
        for j, day in enumerate(dates):
            high = price * (1.14 if i % 4 == 0 and j == 2 else 1.06)
            close = price * (1.03 if i % 2 == 0 else 0.97)
            bars.append({"date": day, "high": high, "close": close})
        rows.append({"ticker": ticker, "source": "SIP", "bars": bars})
    after = datetime.fromisoformat(dates[-1]).replace(
        hour=17, tzinfo=ZoneInfo("America/New_York")).astimezone(timezone.utc)
    return {"run_id": packet["run_id"], "asof_utc": after.isoformat(),
            "session_dates": dates, "rows": rows}


def test_review_uses_high_touch_not_close_and_rejects_early_review(tmp_path, monkeypatch):
    cutoff, _, _, _, locked, frozen = _freeze(tmp_path, monkeypatch)
    outcome = _outcomes(frozen)
    path = _write(tmp_path / "outcome.json", outcome)
    finish_time = datetime.fromisoformat(outcome["asof_utc"])
    monkeypatch.setattr(trial, "_now", lambda: finish_time + timedelta(minutes=1))
    result = trial.review(locked / "trial_frozen.json", path, tmp_path / "review.json")
    assert result["status"] == "EXPERIMENT_ONLY_S5"
    assert result["actual_top20_scope"] == "ORIGINAL_ELIGIBLE_COHORT_ONLY_NOT_FULL_US_MARKET"
    assert result["comparison"]["A_SIMPLE"]["top20_hits"] > 0
    assert result["comparison"]["B_ISSUER_EVENT"]["top20_hits"] > 0
    assert result["comparison"]["C_HASOL_AI"]["top20_hits"] > 0
    assert all(r["top5_hits"] <= 5 for r in result["comparison"].values())
    assert result["candidate_results"]["T000"]["first_hit_session"] == 3
    assert result["candidate_results"]["T000"]["last_close_pct"] == 3
    with pytest.raises(FileExistsError):
        trial.review(locked / "trial_frozen.json", path, tmp_path / "review.json")
    early = copy.deepcopy(outcome)
    early["asof_utc"] = (finish_time - timedelta(hours=2)).isoformat()
    monkeypatch.setattr(trial, "_now", lambda: finish_time + timedelta(minutes=1))
    with pytest.raises(trial.TrialError, match="not closed"):
        trial.review(locked / "trial_frozen.json", _write(tmp_path / "early.json", early),
                     tmp_path / "review-early.json")


def test_modified_frozen_file_cannot_be_retrospectively_reviewed(tmp_path, monkeypatch):
    cutoff, _, _, _, locked, frozen = _freeze(tmp_path, monkeypatch)
    original = locked / "trial_frozen.json"
    data = json.loads(original.read_text())
    data["payload"]["baseline"]["T000"]["price"] = 999
    original.write_text(json.dumps(data))
    outcomes = _outcomes(frozen)
    monkeypatch.setattr(trial, "_now", lambda: datetime.fromisoformat(outcomes["asof_utc"]) + timedelta(hours=1))
    with pytest.raises(trial.TrialError, match="digest mismatch"):
        trial.review(original, _write(tmp_path / "outcome.json", outcomes),
                     tmp_path / "review.json")
