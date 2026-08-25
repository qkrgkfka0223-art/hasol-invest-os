from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def write_run_artifacts(output_dir: Path, universe_df: pd.DataFrame, features_df: pd.DataFrame, ranked_df: pd.DataFrame, top50_df: pd.DataFrame, data_quality: dict, manifest: dict) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "universe_snapshot": output_dir / "universe_snapshot.csv",
        "features": output_dir / "features.csv",
        "full_rank": output_dir / "full_rank.csv",
        "quant_top50": output_dir / "quant_top50.csv",
        "data_quality": output_dir / "data_quality.json",
        "run_manifest": output_dir / "run_manifest.json",
    }
    universe_df.to_csv(paths["universe_snapshot"], index=False)
    features_df.to_csv(paths["features"], index=False)
    ranked_df.to_csv(paths["full_rank"], index=False)
    top50_df.to_csv(paths["quant_top50"], index=False)
    write_json(paths["data_quality"], data_quality)
    manifest = dict(manifest)
    manifest["artifact_sha256"] = {name: sha256_file(path) for name, path in paths.items() if name != "run_manifest" and path.exists()}
    write_json(paths["run_manifest"], manifest)
    return {name: str(path) for name, path in paths.items()}
