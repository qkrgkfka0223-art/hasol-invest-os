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
    pred = build_prediction_row(top20, top5, execution, market_code, market_reason, data_mode=data_mode)
    pred_path = outdir / "prediction_row.csv"
    pred.to_csv(pred_path, index=False)
    paths["prediction_row.csv"] = str(pred_path)
    if run_metadata is not None:
        meta_path = outdir / "run_metadata.json"
        meta = {"hasol_detector_version": VERSION, "created_at_kst": datetime.now(KST).isoformat(), **run_metadata}
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        paths["run_metadata.json"] = str(meta_path)
    return paths

def build_prediction_row(top20: pd.DataFrame, top5: pd.DataFrame, execution: pd.DataFrame, market_code: str, market_reason: str, data_mode: str = "sample") -> pd.DataFrame:
    now = datetime.now(KST)
    events = _top_values(top20, "primary_event", 3)
    axes = _top_values(top20, "primary_axis", 3)
    confidence = "LOW_SAMPLE_LOCKED" if data_mode == "sample" else "MEDIUM_NEEDS_WEB_VALIDATION"
    validation_status = "SAMPLE_ONLY_DO_NOT_TRADE" if data_mode == "sample" else "NEEDS_WEB_VALIDATION"
    row = {
        "prediction_id": f"PRED_{now.strftime('%Y%m%d_%H%M%S')}",
        "date_kst": now.strftime("%Y-%m-%d"),
        "market_code": market_code,
        "market_reason": market_reason,
        "event_1": events[0] if len(events) > 0 else "",
        "event_2": events[1] if len(events) > 1 else "",
        "event_3": events[2] if len(events) > 2 else "",
        "axis_1": axes[0] if len(axes) > 0 else "",
        "axis_2": axes[1] if len(axes) > 1 else "",
        "axis_3": axes[2] if len(axes) > 2 else "",
        "primary_strategy": "뉴스직접수혜/조용한RS",
        "secondary_strategy": "실적후지속/섹터순환",
        "top20": ";".join(top20["ticker"].astype(str).tolist()) if not top20.empty else "",
        "execution_candidates": ";".join(execution["ticker"].astype(str).tolist()) if not execution.empty else "",
        "validation_status": validation_status,
        "data_source": f"{data_mode} + yfinance live-ready + edgartools optional hooks",
        "thesis": "v1.3 감지 엔진: SEC cluster, biotech expansion, famous partner, post-spike stage를 반영해 Top20 압축. 웹 정밀검증 전에는 매수 판단 아님.",
        "confidence": confidence,
        "memo": f"HASOL_DETECTOR_V{VERSION} run; execution locked unless live+manual flag+web validation.",
    }
    for i in range(5):
        if i < len(top5):
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
        "event_tags", "axis_tags", "primary_event", "primary_axis", "famous_partner_hits", "biotech_event_hits", "sec_cluster_flag",
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
        if "BIOTECH_LICENSE" in event_tags or "CLINICAL_SUCCESS" in event_tags or "BLA_ACCEPTED" in event_tags:
            must_verify.append("임상/FDA/BLA/license 원문과 발표 시간 확인")
        if str(r.get("famous_partner_hits", "")):
            must_verify.append("유명 파트너명이 실제 계약/수주인지 단순 언급인지 확인")
        if cap_bucket in ["micro_cap", "nano_cap"]:
            must_verify.append("초저시총 detect-only: offering/dilution/reverse split/delisting 확인")
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
            "event_tags": event_tags,
            "axis_tags": str(r.get("axis_tags", "")),
            "primary_event": str(r.get("primary_event", "")),
            "primary_axis": str(r.get("primary_axis", "")),
            "famous_partner_hits": str(r.get("famous_partner_hits", "")),
            "biotech_event_hits": str(r.get("biotech_event_hits", "")),
            "sec_cluster_flag": r.get("sec_cluster_flag", ""),
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
    if df.empty or col not in df.columns:
        return []
    vals = []
    for v in df[col].astype(str):
        for x in v.split(";"):
            if x and x != "NONE" and x not in vals:
                vals.append(x)
            if len(vals) >= n:
                return vals
    return vals
