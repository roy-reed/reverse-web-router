"""LOCAL_EDGE backend arbitration; Codex remains the final local authority."""
from __future__ import annotations

from typing import Any, Dict, Tuple


def select_local_backend(task: Dict[str, Any], repo_clean: bool, deterministic_acceptance: bool) -> Tuple[str, str]:
    preference = task.get("local_backend_preference", "AUTO")
    kind = task.get("task_kind", "other")
    repository = bool(task.get("repository"))
    implementation = bool(task.get("implementation"))

    if task.get("planning_only") or not implementation:
        return "CODEX_DIRECT", "Planning, review, diagnosis, or non-implementation work stays with Codex"
    runner_eligible = repository and kind == "coding" and repo_clean and deterministic_acceptance
    if preference == "CODING_RUNNER" and not runner_eligible:
        return "NEEDS_USER", "Coding Runner preference cannot bypass repository cleanliness and acceptance gates"
    if preference == "CODEX_DIRECT":
        return "CODEX_DIRECT", "Explicit direct-Codex preference"
    if runner_eligible:
        return "CODING_RUNNER", "Bounded clean repository implementation with deterministic acceptance"
    return "CODEX_DIRECT", "Task is unsuitable for isolated Coding Runner execution"
