#!/usr/bin/env python3
"""Read and update the one canonical rwrouter ledger comment on a GitHub Issue."""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator.github_ledger import (  # noqa: E402
    GitHubClient,
    prepare_claim,
    prepare_paid,
    prepare_result,
    prepare_state,
)


def write_output(path: Path | None, value) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(text)


def github_output(path: str | None, **values) -> None:
    if not path:
        return
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        for key, value in values.items():
            handle.write("%s=%s\n" % (key, str(value).lower() if isinstance(value, bool) else value))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    root.add_argument("--repo", required=True)
    root.add_argument("--api-url", default=os.environ.get("GITHUB_API_URL", "https://api.github.com"))
    root.add_argument("--out", type=Path)
    root.add_argument("--github-output", default=os.environ.get("GITHUB_OUTPUT"))
    sub = root.add_subparsers(dest="command", required=True)

    dependencies = sub.add_parser("dependencies")
    dependencies.add_argument("--task", type=Path, required=True)

    claim = sub.add_parser("claim")
    claim.add_argument("--issue", type=int, required=True)
    claim.add_argument("--task", type=Path, required=True)
    claim.add_argument("--worker", required=True)

    paid = sub.add_parser("mark-paid")
    paid.add_argument("--issue", type=int, required=True)
    paid.add_argument("--task-id", required=True)
    paid.add_argument("--provider-run-id")

    final = sub.add_parser("finalize")
    final.add_argument("--issue", type=int, required=True)
    final.add_argument("--task-id", required=True)
    final.add_argument("--worker-result", type=Path, required=True)

    state = sub.add_parser("state")
    state.add_argument("--issue", type=int, required=True)
    state.add_argument("--task-id", required=True)
    state.add_argument("--worker", default="auto")
    state.add_argument("--state", required=True)
    state.add_argument("--summary", default="")
    return root


def main() -> int:
    args = parser().parse_args()
    client = GitHubClient(os.environ.get("GITHUB_TOKEN", ""), args.api_url)
    if args.command == "dependencies":
        task = json.loads(args.task.read_text(encoding="utf-8"))
        states = client.dependency_states(args.repo, task.get("depends_on") or [])
        write_output(args.out, states)
        github_output(args.github_output, count=len(states))
        return 0

    task_id = args.task_id if hasattr(args, "task_id") else json.loads(args.task.read_text(encoding="utf-8"))["task_id"]
    comment_id, existing = client.ledger(args.repo, args.issue, task_id)

    if args.command == "claim":
        declared_issue = client.find_task_issue(args.repo, task_id)
        if declared_issue != args.issue:
            raise SystemExit("task_id must be declared by exactly this Issue")
        record, dispatchable = prepare_claim(existing, task_id, args.worker)
        if dispatchable:
            comment_id = client.write_ledger(args.repo, args.issue, comment_id, record)
        payload = {"comment_id": comment_id, "dispatchable": dispatchable, "record": record}
        write_output(args.out, payload)
        github_output(args.github_output, dispatchable=dispatchable, comment_id=comment_id or "")
        return 0

    if args.command == "state" and existing is None:
        existing, _ = prepare_claim(None, task_id, args.worker)
    if existing is None:
        raise SystemExit("canonical ledger comment does not exist")

    if args.command == "mark-paid":
        run_id = args.provider_run_id or "pending-" + str(uuid.uuid4())
        record = prepare_paid(existing, run_id)
    elif args.command == "finalize":
        if args.worker_result.is_file():
            result = json.loads(args.worker_result.read_text(encoding="utf-8"))
        else:
            result = {"result": None, "errors": ["worker step did not produce a result"]}
        record = prepare_result(existing, result)
    else:
        record = prepare_state(existing, args.state, args.summary)
    comment_id = client.write_ledger(args.repo, args.issue, comment_id, record)
    write_output(args.out, {"comment_id": comment_id, "record": record})
    github_output(args.github_output, comment_id=comment_id, state=record["state"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
