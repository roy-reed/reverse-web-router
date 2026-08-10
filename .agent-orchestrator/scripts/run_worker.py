#!/usr/bin/env python3
"""Run one provider-neutral worker with dry-run as the safe default."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator.claims import claim_task, update_claim  # noqa: E402
from orchestrator.schema import validate_work_unit  # noqa: E402
from orchestrator.security import ensure_cloud_safe, redact, redact_known_values  # noqa: E402
from orchestrator.worker import DeepSeekWorkerAdapter, FakeWorkerAdapter  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--claim-dir", type=Path, default=Path(".rwr-state/claims"))
    parser.add_argument("--out", type=Path, default=Path(".rwr-state/worker-result.json"))
    parser.add_argument("--adapter", choices=["fake", "deepseek"], default="fake")
    args = parser.parse_args()
    task = json.loads(args.task.read_text(encoding="utf-8"))
    errors = validate_work_unit(task)
    if errors:
        raise SystemExit("invalid task: " + "; ".join(errors))
    ensure_cloud_safe(task)
    claim_task(args.claim_dir, task["task_id"], args.adapter)
    adapter = FakeWorkerAdapter() if args.adapter == "fake" else DeepSeekWorkerAdapter()
    try:
        result = adapter.run(task) if args.adapter == "fake" else adapter.run(task, str(args.claim_dir))
        update_claim(args.claim_dir, task["task_id"], "verifying", result.provider_run_id)
        record = {"task_id": task["task_id"], "result": result.to_dict(), "errors": []}
        exit_code = 0
    except Exception as exc:
        update_claim(args.claim_dir, task["task_id"], "failed")
        record = {"task_id": task["task_id"], "result": None, "errors": [type(exc).__name__ + ": " + str(exc)]}
        exit_code = 4
    safe_record = redact_known_values(redact(record), [os.environ.get("DEEPSEEK_API_KEY", "")])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(safe_record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(safe_record, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
