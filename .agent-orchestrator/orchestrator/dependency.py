"""Dependency gates for bounded work units.

A work unit becomes dispatchable only when every task in ``depends_on`` is in
an accepted state. Missing state records, still-running dependencies, or
failed/cancelled dependencies all block dispatch with an explicit reason.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

SATISFIED_STATES = ("accepted",)


@dataclass
class DependencyResult:
    ready: bool
    unsatisfied: List[Tuple[str, str]] = field(default_factory=list)
    failed: List[Tuple[str, str]] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)

    def reasons(self) -> List[str]:
        out = []
        for task_id, state in self.unsatisfied:
            out.append("dependency %s is in state %r (not accepted)" % (task_id, state))
        for task_id, state in self.failed:
            out.append("dependency %s is in state %r (failed/cancelled)" % (task_id, state))
        for task_id in self.missing:
            out.append("dependency %s has no state record" % (task_id,))
        return out


def check_dependencies(task: Dict[str, Any], states: Dict[str, str]) -> DependencyResult:
    """Check ``task["depends_on"]`` against the ``task_id -> state`` map."""
    deps = task.get("depends_on") or []
    unsatisfied: List[Tuple[str, str]] = []
    failed: List[Tuple[str, str]] = []
    missing: List[str] = []
    for dep in deps:
        state = states.get(dep)
        if state is None:
            missing.append(dep)
        elif state in SATISFIED_STATES:
            continue
        elif state in ("failed", "cancelled"):
            failed.append((dep, state))
        else:
            unsatisfied.append((dep, state))
    ready = not (unsatisfied or failed or missing)
    return DependencyResult(ready=ready, unsatisfied=unsatisfied, failed=failed, missing=missing)


def gate_dispatchable(
    task: Dict[str, Any],
    states: Dict[str, str],
    contract_valid: bool = True,
    claim_ok: bool = True,
) -> Tuple[bool, List[str]]:
    """Full dispatch gate: valid contract, satisfied dependencies, fresh claim."""
    reasons: List[str] = []
    if not contract_valid:
        reasons.append("contract is invalid")
    if not claim_ok:
        reasons.append("task is already claimed or paid-invoked")
    result = check_dependencies(task, states)
    reasons.extend(result.reasons())
    return (not reasons), reasons
