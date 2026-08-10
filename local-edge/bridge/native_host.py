#!/usr/bin/env python3
"""Native Messaging LOCAL_EDGE host. It never opens a network listener."""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".agent-orchestrator"))
sys.path.insert(0, str(ROOT / "local-edge"))

from orchestrator.local_backend import select_local_backend  # noqa: E402
from translator import sanitized_receipt, v11_to_v2  # noqa: E402

MAX_MESSAGE_BYTES = 1024 * 1024


def read_message(stream) -> dict | None:
    header = stream.read(4)
    if not header:
        return None
    if len(header) != 4:
        raise ValueError("truncated Native Messaging header")
    length = struct.unpack("<I", header)[0]
    if length <= 0 or length > MAX_MESSAGE_BYTES:
        raise ValueError("Native Messaging payload size is invalid")
    payload = stream.read(length)
    if len(payload) != length:
        raise ValueError("truncated Native Messaging payload")
    return json.loads(payload.decode("utf-8"))


def write_message(stream, message: dict) -> None:
    payload = json.dumps(message, ensure_ascii=False).encode("utf-8")
    stream.write(struct.pack("<I", len(payload)))
    stream.write(payload)
    stream.flush()


def handle(request: dict, config: dict) -> dict:
    binding = request.get("project_fingerprint")
    if not binding or binding != config.get("bound_project_fingerprint"):
        raise ValueError("handoff does not belong to the bound ChatGPT Project")
    envelope = v11_to_v2(request.get("packet") or {})
    alias = (envelope.get("project") or {}).get("workspace_alias")
    aliases = config.get("workspace_aliases") or {}
    if alias not in aliases:
        raise ValueError("unknown workspace_alias")
    edge = envelope.get("edge") or {}
    task = {
        "local_backend_preference": edge.get("local_backend_preference", "AUTO"),
        "task_kind": edge.get("task_kind", "other"),
        "repository": bool(config.get("repository_aliases", {}).get(alias)),
        "implementation": request.get("implementation") is True,
        "planning_only": request.get("planning_only") is True,
    }
    backend, reason = select_local_backend(
        task,
        repo_clean=request.get("repo_clean") is True,
        deterministic_acceptance=bool(envelope.get("acceptance_criteria", {}).get("definition_of_done")),
    )
    receipt = sanitized_receipt(envelope["task_id"], "accepted", backend, reason)
    receipt["workspace_alias"] = alias
    receipt["dry_run"] = True
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    while True:
        try:
            message = read_message(sys.stdin.buffer)
            if message is None:
                return 0
            write_message(sys.stdout.buffer, {"ok": True, "receipt": handle(message, config)})
        except Exception as exc:
            write_message(sys.stdout.buffer, {"ok": False, "error": type(exc).__name__ + ": " + str(exc)})


if __name__ == "__main__":
    raise SystemExit(main())
