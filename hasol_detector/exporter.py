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
        "thesis": "1차 감지 엔진: 이벤트+상대강도+시총버킷 분산으로 Top20 압축. 웹 정밀검증 전에는 매수 판단 아님.",
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
    if top20 is None or top20.empty:
        return pd.DataFrame(columns=["rank", "ticker", "company", "event_tags", "axis_tags", "detect_price", "cap_bucket", "web_query", "verify_news", "verify_price", "verify_risk", "decision_after_web"])
    rows = []
    for _, r in top20.sort_values("top20_rank").iterrows():
        ticker = str(r.get("ticker", ""))
        company = str(r.get("company", ticker))
        rows.append({
            "rank": int(r.get("top20_rank", 0)),
            "ticker": ticker,
            "company": company,
            "event_tags": str(r.get("event_tags", "")),
            "axis_tags": str(r.get("axis_tags", "")),
            "detect_price": r.get("price", ""),
            "cap_bucket": r.get("cap_bucket", ""),
            "web_query": f"{ticker} {company} latest news SEC filing stock catalyst offering dilution",
            "verify_news": "원문 뉴스/공시 시간, 이벤트 품질, 후행뉴스 여부 확인",
            "verify_price": "현재가, detect_price 대비, 고점/저점, 윗꼬리, 거래량 지속 확인",
            "verify_risk": "offering/dilution, delisting, 초저시총 펌핑, 3일 포물선 확인",
            "decision_after_web": "KEEP / WATCH / REJECT / EXECUTION_CANDIDATE",
        })
    return pd.DataFrame(rows)

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
