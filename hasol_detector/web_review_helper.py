from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd

VALID_DECISIONS = {"KEEP", "WATCH", "REJECT", "READY_FOR_MANUAL_REVIEW", ""}


def load_review_file(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "decision_after_web" not in df.columns:
        df["decision_after_web"] = ""
    if "decision_reason" not in df.columns:
        df["decision_reason"] = ""
    df["decision_after_web"] = df["decision_after_web"].fillna("").astype(str).str.strip()
    unknown = sorted(set(df["decision_after_web"]) - VALID_DECISIONS)
    if unknown:
        raise ValueError(f"Unknown decisions: {unknown}. Use {sorted(VALID_DECISIONS)}")
    return df


def export_review_outputs(review_csv: str, output_dir: str) -> dict[str, str]:
    df = load_review_file(review_csv)
    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    keep_watch = df[df["decision_after_web"].isin(["KEEP", "WATCH", "READY_FOR_MANUAL_REVIEW"])].copy()
    rejected = df[df["decision_after_web"].eq("REJECT")].copy()
    top5 = keep_watch.sort_values(["decision_after_web", "total_score"], ascending=[True, False]).head(5).copy() if "total_score" in keep_watch.columns else keep_watch.head(5).copy()

    paths = {
        "validated_top20.csv": str(outdir / "validated_top20.csv"),
        "validated_top5.csv": str(outdir / "validated_top5.csv"),
        "rejected_after_web.csv": str(outdir / "rejected_after_web.csv"),
    }
    keep_watch.to_csv(paths["validated_top20.csv"], index=False)
    top5.to_csv(paths["validated_top5.csv"], index=False)
    rejected.to_csv(paths["rejected_after_web.csv"], index=False)
    return paths


def main():
    parser = argparse.ArgumentParser(description="HASOL v1.3 web review helper")
    parser.add_argument("--review-csv", required=True, help="Edited web_validation_checklist.csv")
    parser.add_argument("--output-dir", default="output_reviewed")
    args = parser.parse_args()
    paths = export_review_outputs(args.review_csv, args.output_dir)
    for k, v in paths.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
