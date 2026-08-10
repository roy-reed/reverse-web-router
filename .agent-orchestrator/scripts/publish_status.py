#!/usr/bin/env python3
"""Render a canonical machine status record and human-readable Issue comment."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator.security import ensure_cloud_safe, redact  # noqa: E402
from orchestrator.state import TASK_STATES  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    status = json.loads(args.status.read_text(encoding="utf-8"))
    if status.get("state") not in TASK_STATES:
        raise SystemExit("unknown canonical task state")
    safe = {
        "schema": "agent-status/v1",
        "task_id": status["task_id"],
        "state": status["state"],
        "provider_run_id": status.get("provider_run_id"),
        "checks": status.get("checks", []),
        "summary": status.get("summary", ""),
    }
    safe = redact(safe)
    ensure_cloud_safe(safe)
    body = "<!-- rwrouter-status\n%s\n-->\n\n**Agent status:** `%s`\n\n%s\n" % (
        json.dumps(safe, ensure_ascii=False, sort_keys=True),
        safe["state"],
        safe["summary"],
    )
    if args.out:
        args.out.write_text(body, encoding="utf-8", newline="\n")
    else:
        print(body, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
