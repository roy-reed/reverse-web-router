#!/usr/bin/env python3
"""Extract and validate one agent-task/v1 contract from an Issue body."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator.schema import validate_work_unit  # noqa: E402
from orchestrator.security import ensure_cloud_safe  # noqa: E402
from orchestrator.yamlmini import parse as parse_yaml  # noqa: E402

FENCE = re.compile(r"```(json|ya?ml)\s*\n(.*?)\n```", re.I | re.S)


def extract_contract(text: str):
    matches = FENCE.findall(text)
    if len(matches) != 1:
        raise ValueError("Issue body must contain exactly one json/yaml fenced task contract")
    language, body = matches[0]
    return json.loads(body) if language.lower() == "json" else parse_yaml(body)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--body-file", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--github-output", default=os.environ.get("GITHUB_OUTPUT"))
    args = parser.parse_args()
    text = args.body_file.read_text(encoding="utf-8") if args.body_file else sys.stdin.read()
    contract = extract_contract(text)
    errors = validate_work_unit(contract)
    if errors:
        raise SystemExit("invalid contract: " + "; ".join(errors))
    ensure_cloud_safe(contract)
    output = json.dumps(contract, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(output)
    if args.github_output:
        with open(args.github_output, "a", encoding="utf-8", newline="\n") as handle:
            handle.write("task_id=%s\n" % contract["task_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
