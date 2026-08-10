"""Atomic task claiming and paid-invocation idempotency."""
from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .errors import ClaimConflictError, DuplicatePaidInvocationError
from .state import TASK_STATES

TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,127}$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _path(root: Path, task_id: str) -> Path:
    if not TASK_ID_RE.fullmatch(task_id):
        raise ValueError("unsafe task_id")
    return root / (task_id + ".json")


def _read(path: Path) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _replace_json(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(record, fh, ensure_ascii=False, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def claim_task(root: Path, task_id: str, worker: str) -> Dict[str, Any]:
    """Create one claim atomically; repeated claims resolve to the existing record."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    path = _path(root, task_id)
    record = {
        "task_id": task_id,
        "worker": worker,
        "state": "claimed",
        "claimed_at": _now(),
        "paid_invoked": False,
        "provider_run_id": None,
    }
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        existing = _read(path)
        if existing.get("worker") != worker:
            raise ClaimConflictError("task %s is already claimed by %s" % (task_id, existing.get("worker")))
        return existing
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(record, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    return record


def mark_paid_invocation(root: Path, task_id: str, provider_run_id: Optional[str] = None) -> Dict[str, Any]:
    """Mark the paid boundary before network invocation; a second call fails closed."""
    path = _path(Path(root), task_id)
    record = _read(path)
    if record.get("paid_invoked"):
        raise DuplicatePaidInvocationError("paid invocation already recorded for %s" % task_id)
    record["paid_invoked"] = True
    record["invoked_at"] = _now()
    record["provider_run_id"] = provider_run_id
    record["state"] = "running"
    _replace_json(path, record)
    return record


def update_claim(root: Path, task_id: str, state: str, provider_run_id: Optional[str] = None) -> Dict[str, Any]:
    if state not in TASK_STATES:
        raise ValueError("unknown canonical task state %r" % state)
    path = _path(Path(root), task_id)
    record = _read(path)
    record["state"] = state
    record["updated_at"] = _now()
    if provider_run_id is not None:
        record["provider_run_id"] = provider_run_id
    _replace_json(path, record)
    return record
