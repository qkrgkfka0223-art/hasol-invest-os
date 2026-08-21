from __future__ import annotations

import argparse
import json
from pathlib import Path

from hasol_runtime import HasolRuntime


def main() -> int:
    parser = argparse.ArgumentParser(description="Run HASOL Model Loop v3 on a frozen input artifact")
    parser.add_argument("input", type=Path, help="Frozen run input JSON")
    parser.add_argument("--output", type=Path, default=Path("hasol_run_result.json"))
    parser.add_argument("--readback-hash", default=None, help="External Brain prediction hash after independent readback")
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    runtime = HasolRuntime(payload)
    result = runtime.run()
    if args.readback_hash:
        result = HasolRuntime.close_after_readback(result, args.readback_hash)

    args.output.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    print(json.dumps({
        "outcome": result.get("outcome"),
        "state": result.get("state"),
        "official_prediction": result.get("official_prediction"),
        "prediction_hash": result.get("prediction_hash"),
        "output": str(args.output),
    }, ensure_ascii=False))
    return 0 if result.get("state") in {"WRITE_READY", "CLOSED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
