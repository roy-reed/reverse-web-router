#!/usr/bin/env python3
"""Check changed paths against one work-unit contract."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator.boundary import check_changed_paths  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--base", default="HEAD^")
    parser.add_argument("--changed-file", action="append", default=[])
    args = parser.parse_args()
    task = json.loads(args.task.read_text(encoding="utf-8"))
    changed = list(args.changed_file)
    if args.repo:
        result = subprocess.run(
            ["git", "-C", str(args.repo), "diff", "--name-only", args.base, "--"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        changed.extend(line for line in result.stdout.splitlines() if line)
    outside, forbidden = check_changed_paths(changed, task["allowed_paths"], task["forbidden_paths"])
    report = {"ok": not outside and not forbidden, "changed": changed, "outside_allowed": outside, "forbidden": forbidden}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
