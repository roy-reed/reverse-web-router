#!/usr/bin/env python3
"""Evaluate dependency readiness from a task contract and task-state map."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator.dependency import gate_dispatchable  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--states", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--github-output", default=os.environ.get("GITHUB_OUTPUT"))
    parser.add_argument("--soft", action="store_true", help="Report blocked without failing the workflow step")
    args = parser.parse_args()
    task = json.loads(args.task.read_text(encoding="utf-8"))
    states = json.loads(args.states.read_text(encoding="utf-8"))
    ready, reasons = gate_dispatchable(task, states)
    report = {"ready": ready, "reasons": reasons}
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.write_text(output, encoding="utf-8", newline="\n")
    else:
        print(output, end="")
    if args.github_output:
        with open(args.github_output, "a", encoding="utf-8", newline="\n") as handle:
            handle.write("ready=%s\n" % str(ready).lower())
    return 0 if ready or args.soft else 2


if __name__ == "__main__":
    raise SystemExit(main())
