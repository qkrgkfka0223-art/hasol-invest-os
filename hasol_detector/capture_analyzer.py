from __future__ import annotations

from pathlib import Path
import json
import pandas as pd


def _load(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        return pd.DataFrame(columns=["ticker"])
    df = pd.read_csv(p)
    if "ticker" in df.columns:
        df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    return df


def _stage(ticker: str, sets: dict[str, set[str]]) -> tuple[str, str]:
    if ticker in sets["execution"]:
        return "EXECUTION_CAPTURE", "CAPTURED_EXECUTION"
    if ticker in sets["top5"]:
        return "TOP5_CAPTURE", "CAPTURED_TOP5"
    if ticker in sets["top20"]:
        return "TOP20_CAPTURE", "CAPTURED_TOP20"
    if ticker in sets["rejected"]:
        return "REJECTED_AFTER_DETECTION", "FILTER_FAIL"
    if ticker in sets["scored"]:
        return "SCORED_NOT_COMPRESSED", "COMPRESSION_FAIL"
    if ticker in sets["raw_candidates"]:
        return "RAW_ONLY", "FILTER_FAIL"
    return "NOT_IN_CANDIDATE_POOL", "DETECTION_FAIL"


def analyze_capture(movers_csv: str, detector_output_dir: str, output_dir: str) -> dict[str, str]:
    movers = _load(movers_csv)
    base = Path(detector_output_dir)
    files = {
        "raw_candidates": _load(base / "raw_candidates.csv"),
        "scored": _load(base / "scored_candidates.csv"),
        "rejected": _load(base / "rejected_candidates.csv"),
        "top20": _load(base / "top20_candidates.csv"),
        "top5": _load(base / "top5_candidates.csv"),
        "execution": _load(base / "execution_candidates.csv"),
    }
    sets = {k: set(v.get("ticker", [])) for k, v in files.items()}
    scored = files["scored"]
    lookup = scored.set_index("ticker").to_dict("index") if not scored.empty and "ticker" in scored.columns else {}

    rows = []
    for _, r in movers.iterrows():
        t = str(r.get("ticker", "")).upper().strip()
        stage, miss = _stage(t, sets)
        s = lookup.get(t, {})
        rows.append({
            "date": r.get("date", ""),
            "rank": r.get("rank", ""),
            "ticker": t,
            "return_1d": r.get("return_1d", ""),
            "capture_stage": stage,
            "miss_type": miss,
            "was_in_raw": t in sets["raw_candidates"],
            "was_scored": t in sets["scored"],
            "was_rejected": t in sets["rejected"],
            "was_top20": t in sets["top20"],
            "was_top5": t in sets["top5"],
            "was_execution": t in sets["execution"],
            "detector_score": s.get("total_score", ""),
            "event_tags": s.get("event_tags", ""),
            "axis_tags": s.get("axis_tags", ""),
            "candidate_source": s.get("candidate_source", ""),
        })
    report = pd.DataFrame(rows)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / "mover_capture_report.csv"
    missed_path = out / "missed_movers.csv"
    summary_path = out / "backtest_summary.json"
    report.to_csv(report_path, index=False)
    missed = report[report["miss_type"].isin(["DETECTION_FAIL", "FILTER_FAIL", "COMPRESSION_FAIL"])] if not report.empty else report
    missed.to_csv(missed_path, index=False)
    summary = {
        "mover_count": int(len(report)),
        "raw_capture_rate": round(float(report["was_in_raw"].mean()), 4) if not report.empty else 0,
        "top20_capture_rate": round(float(report["was_top20"].mean()), 4) if not report.empty else 0,
        "top5_capture_rate": round(float(report["was_top5"].mean()), 4) if not report.empty else 0,
        "execution_capture_rate": round(float(report["was_execution"].mean()), 4) if not report.empty else 0,
        "detection_fail_count": int((report["miss_type"] == "DETECTION_FAIL").sum()) if not report.empty else 0,
        "filter_fail_count": int((report["miss_type"] == "FILTER_FAIL").sum()) if not report.empty else 0,
        "compression_fail_count": int((report["miss_type"] == "COMPRESSION_FAIL").sum()) if not report.empty else 0,
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"mover_capture_report.csv": str(report_path), "missed_movers.csv": str(missed_path), "backtest_summary.json": str(summary_path)}
