#!/usr/bin/env python3
"""Claim or update one work unit using an atomic local claim ledger."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator.claims import claim_task, mark_paid_invocation, update_claim  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["claim", "mark-paid", "update"])
    parser.add_argument("task_id")
    parser.add_argument("--claim-dir", type=Path, default=Path(".rwr-state/claims"))
    parser.add_argument("--worker", default="auto")
    parser.add_argument("--state", default="running")
    parser.add_argument("--provider-run-id")
    args = parser.parse_args()
    if args.action == "claim":
        record = claim_task(args.claim_dir, args.task_id, args.worker)
    elif args.action == "mark-paid":
        record = mark_paid_invocation(args.claim_dir, args.task_id, args.provider_run_id)
    else:
        record = update_claim(args.claim_dir, args.task_id, args.state, args.provider_run_id)
    print(json.dumps(record, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
