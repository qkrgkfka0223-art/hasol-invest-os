from __future__ import annotations
import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone, timedelta
from .config import VERSION

KST = timezone(timedelta(hours=9))

def export_results(output_dir: str, raw: pd.DataFrame, scored: pd.DataFrame, filtered: pd.DataFrame, rejected: pd.DataFrame, top20: pd.DataFrame, top5: pd.DataFrame, execution: pd.DataFrame, market_code: str, market_reason: str, data_mode: str = "sample", run_metadata: dict | None = None) -> dict[str, str]:
    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    paths = {}
    frames = {
        "raw_candidates.csv": raw,
        "tagged_candidates.csv": raw,
        "scored_candidates.csv": scored,
        "filtered_candidates.csv": filtered,
        "rejected_candidates.csv": rejected,
        "top20_candidates.csv": top20,
        "top5_candidates.csv": top5,
        "execution_candidates.csv": execution,
        "web_validation_checklist.csv": build_web_validation_checklist(top20),
    }
    for name, frame in frames.items():
        p = outdir / name
        frame.to_csv(p, index=False)
        paths[name] = str(p)
    pred = build_prediction_row(top20, top5, execution, market_code, market_reason, data_mode=data_mode, run_metadata=run_metadata or {})
    pred_path = outdir / "prediction_row.csv"
    pred.to_csv(pred_path, index=False)
    paths["prediction_row.csv"] = str(pred_path)
    if run_metadata is not None:
        meta_path = outdir / "run_metadata.json"
        meta = {"hasol_detector_version": VERSION, "created_at_kst": datetime.now(KST).isoformat(), **run_metadata}
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        paths["run_metadata.json"] = str(meta_path)
    return paths

def build_prediction_row(top20: pd.DataFrame, top5: pd.DataFrame, execution: pd.DataFrame, market_code: str, market_reason: str, data_mode: str = "sample", run_metadata: dict | None = None) -> pd.DataFrame:
    run_metadata = run_metadata or {}
    now = datetime.now(KST)
    events = _top_values(top20, "primary_event", 3)
    axes = _top_values(top20, "primary_axis", 3)
    confidence = "LOW_SAMPLE_LOCKED" if data_mode == "sample" else "MEDIUM_NEEDS_WEB_VALIDATION"
    validation_status = "SAMPLE_ONLY_DO_NOT_TRADE" if data_mode == "sample" else "NEEDS_WEB_VALIDATION"
    event_tagged = int(run_metadata.get("event_tagged_count", 0) or 0)
    candidate_pool_count = int(run_metadata.get("candidate_pool_count", len(top20) if top20 is not None else 0) or 0)
    rejected_list = ";".join(rejected for rejected in _safe_list(top20, "ticker")[:0])
    row = {
        "prediction_id": f"PRED_{now.strftime('%Y%m%d_%H%M%S')}",
        "date_kst": now.strftime("%Y-%m-%d"),
        "market_code": market_code,
        "market_reason": market_reason,
        "scenario_top3": ";".join(axes[:3]) if axes else "NEEDS_SCENARIO_ENGINE",
        "scenario_probs": "NEEDS_SCENARIO_ENGINE",
        "candidate_pool_count": candidate_pool_count,
        "discovery_candidate_count": candidate_pool_count,
        "event_tagged_count": event_tagged,
        "event_none_count": int(run_metadata.get("event_tag_none_count", 0) or 0),
        "event_1": events[0] if len(events) > 0 else "",
        "event_2": events[1] if len(events) > 1 else "",
        "event_3": events[2] if len(events) > 2 else "",
        "axis_1": axes[0] if len(axes) > 0 else "",
        "axis_2": axes[1] if len(axes) > 1 else "",
        "axis_3": axes[2] if len(axes) > 2 else "",
        "primary_strategy": "event_first_candidate_builder",
        "secondary_strategy": "quiet_rs_after_event_validation",
        "top20": ";".join(top20["ticker"].astype(str).tolist()) if top20 is not None and not top20.empty else "",
        "top5_scores": _top5_score_text(top5),
        "execution_candidates": ";".join(execution["ticker"].astype(str).tolist()) if execution is not None and not execution.empty else "",
        "rejected_candidates": rejected_list,
        "validation_status": validation_status,
        "data_source": f"{data_mode} + v1.4 candidate_builder + yfinance + sec_scanner optional hooks",
        "code_version": VERSION,
        "run_id": f"RUN_{now.strftime('%Y%m%d_%H%M%S')}",
        "thesis": "v1.4 후보수집 엔진: universe_seed만 보는 구조를 버리고 price/news/earnings/biotech discovery sources를 합쳐 raw candidate pool을 만든다. 웹 정밀검증 전에는 매수 판단 아님.",
        "confidence": confidence,
        "memo": f"HASOL_DETECTOR_V{VERSION} run; execution locked unless live+manual flag+web validation. 후보수집은 discovery-only이며 원문 검증 필요.",
        "record_status": "COMPLETE_NEEDS_WEB_VALIDATION",
        "missing_fields": "scenario_probs" if not axes else "",
    }
    for i in range(5):
        if top5 is not None and i < len(top5):
            r = top5.iloc[i]
            row[f"top{i+1}"] = r["ticker"]
            row[f"top{i+1}_detect_price"] = round(float(r.get("price", 0)), 2)
        else:
            row[f"top{i+1}"] = ""
            row[f"top{i+1}_detect_price"] = ""
    return pd.DataFrame([row])

def build_web_validation_checklist(top20: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "rank", "ticker", "company", "detect_price", "cap_bucket", "market_cap", "change_pct", "relative_volume",
        "candidate_source", "source_count", "source_confidence", "candidate_reason",
        "event_tags", "axis_tags", "primary_event", "primary_axis", "famous_partner_hits", "biotech_event_hits", "sec_cluster_flag", "bad_event_hits",
        "post_spike_stage", "review_lock_reason", "detect_only_reason", "total_score",
        "web_query", "sec_query", "price_query", "must_verify", "risk_flags_to_check", "decision_after_web", "decision_reason"
    ]
    if top20 is None or top20.empty:
        return pd.DataFrame(columns=cols)
    rows = []
    for _, r in top20.sort_values("top20_rank").iterrows():
        ticker = str(r.get("ticker", ""))
        company = str(r.get("company", ticker))
        event_tags = str(r.get("event_tags", ""))
        cap_bucket = str(r.get("cap_bucket", ""))
        must_verify = []
        if "SEC_CLUSTER" in event_tags or str(r.get("sec_cluster_flag", "")).lower() == "true":
            must_verify.append("최근 5거래일 Form 3/4/13D/13G/8-K cluster 원문 확인")
        if "BIOTECH_LICENSE" in event_tags or "CLINICAL_SUCCESS" in event_tags or "BLA_ACCEPTED" in event_tags or "FDA" in event_tags:
            must_verify.append("임상/FDA/BLA/NDA/PDUFA 원문과 발표 시간 확인")
        if "EARNINGS" in event_tags or "GUIDANCE_RAISE" in event_tags or "BACKLOG_INCREASE" in event_tags:
            must_verify.append("실적 발표 원문, 가이던스, 컨센서스 대비 서프라이즈 확인")
        if str(r.get("famous_partner_hits", "")):
            must_verify.append("유명 파트너명이 실제 계약/수주인지 단순 언급인지 확인")
        if str(r.get("source_confidence", "")).startswith("DISCOVERY_ONLY"):
            must_verify.append("discovery-only 후보: 원문 catalyst 검증 전 실행 금지")
        if cap_bucket in ["micro_cap", "nano_cap"]:
            must_verify.append("초저시총 detect-only: offering/dilution/reverse split/delisting 확인")
        if str(r.get("bad_event_hits", "")):
            must_verify.append("bad_event_hits 원문 확인 후 REJECT/LOCK 검토")
        if str(r.get("post_spike_stage", "")) in ["day2_continuation", "day3_parabolic", "post_climax_fade"]:
            must_verify.append("post-spike stage: 추격 금지/복기 전환 여부 확인")
        rows.append({
            "rank": int(r.get("top20_rank", 0)),
            "ticker": ticker,
            "company": company,
            "detect_price": r.get("price", ""),
            "cap_bucket": cap_bucket,
            "market_cap": r.get("market_cap", ""),
            "change_pct": r.get("change_pct", ""),
            "relative_volume": r.get("relative_volume", ""),
            "candidate_source": str(r.get("candidate_source", "")),
            "source_count": r.get("source_count", ""),
            "source_confidence": str(r.get("source_confidence", "")),
            "candidate_reason": str(r.get("candidate_reason", "")),
            "event_tags": event_tags,
            "axis_tags": str(r.get("axis_tags", "")),
            "primary_event": str(r.get("primary_event", "")),
            "primary_axis": str(r.get("primary_axis", "")),
            "famous_partner_hits": str(r.get("famous_partner_hits", "")),
            "biotech_event_hits": str(r.get("biotech_event_hits", "")),
            "sec_cluster_flag": r.get("sec_cluster_flag", ""),
            "bad_event_hits": str(r.get("bad_event_hits", "")),
            "post_spike_stage": str(r.get("post_spike_stage", "")),
            "review_lock_reason": str(r.get("review_lock_reason", "")),
            "detect_only_reason": str(r.get("detect_only_reason", "")),
            "total_score": r.get("total_score", ""),
            "web_query": f"{ticker} {company} latest news catalyst stock offering dilution delisting",
            "sec_query": f"{ticker} SEC filings Form 4 13D 13G 8-K latest",
            "price_query": f"{ticker} stock price intraday high volume premarket afterhours",
            "must_verify": " | ".join(must_verify) if must_verify else "뉴스 원문/현재가/거래량/후행뉴스 여부 확인",
            "risk_flags_to_check": "offering; dilution; warrant; reverse split; delisting; halt; investigation; 3-day parabolic; long upper wick",
            "decision_after_web": "KEEP / WATCH / REJECT / READY_FOR_MANUAL_REVIEW",
            "decision_reason": "",
        })
    return pd.DataFrame(rows)[cols]

def _top_values(df: pd.DataFrame, col: str, n: int) -> list[str]:
    if df is None or df.empty or col not in df.columns:
        return []
    vals = []
    for v in df[col].astype(str):
        for x in v.split(";"):
            if x and x != "NONE" and x not in vals:
                vals.append(x)
            if len(vals) >= n:
                return vals
    return vals

def _top5_score_text(top5: pd.DataFrame) -> str:
    if top5 is None or top5.empty:
        return ""
    items = []
    for _, r in top5.iterrows():
        items.append(f"{r.get('ticker')}:{r.get('total_score')}")
    return ";".join(items)

def _safe_list(df: pd.DataFrame, col: str) -> list[str]:
    if df is None or df.empty or col not in df.columns:
        return []
    return [str(x) for x in df[col].tolist()]
