"""GitHub control-plane state machine (task and run level).

The authoritative state lives in a structured task record; issue labels are
only a visibility convenience. Unknown events and unknown states fail closed.
"""
from __future__ import annotations

from typing import Dict

from .errors import StateTransitionError

TASK_STATES = (
    "draft",
    "ready",
    "queued",
    "claimed",
    "running",
    "pr-open",
    "verifying",
    "changes-requested",
    "accepted",
    "blocked",
    "waiting-local",
    "failed",
    "cancelled",
)

TERMINAL_TASK_STATES = ("accepted", "failed", "cancelled")

TASK_TRANSITIONS: Dict[str, Dict[str, str]] = {
    "draft": {"VALIDATE": "ready", "CANCEL": "cancelled", "FAIL": "failed"},
    "ready": {"QUEUE": "queued", "CLAIM": "claimed", "BLOCK": "blocked", "CANCEL": "cancelled"},
    "queued": {"CLAIM": "claimed", "BLOCK": "blocked", "CANCEL": "cancelled", "REQUEUE": "ready"},
    "claimed": {"START": "running", "RELEASE": "ready", "FAIL": "failed", "BLOCK": "blocked", "CANCEL": "cancelled"},
    "running": {"PR_OPEN": "pr-open", "FAIL": "failed", "BLOCK": "blocked", "WAIT_LOCAL": "waiting-local", "CANCEL": "cancelled"},
    "pr-open": {"VERIFY": "verifying", "FAIL": "failed", "BLOCK": "blocked", "WAIT_LOCAL": "waiting-local", "CANCEL": "cancelled"},
    "verifying": {"ACCEPT": "accepted", "REQUEST_CHANGES": "changes-requested", "FAIL": "failed", "WAIT_LOCAL": "waiting-local", "CANCEL": "cancelled"},
    "changes-requested": {"REQUEUE": "ready", "FAIL": "failed", "CANCEL": "cancelled"},
    "blocked": {"UNBLOCK": "ready", "CANCEL": "cancelled"},
    "waiting-local": {"RESUME": "pr-open", "ACCEPT": "accepted", "FAIL": "failed", "CANCEL": "cancelled"},
    "accepted": {"REOPEN": "ready"},
    "failed": {"REQUEUE": "ready"},
    "cancelled": {"REOPEN": "ready"},
}

TASK_EVENTS = frozenset(event for mapping in TASK_TRANSITIONS.values() for event in mapping)

RUN_STATES = ("planning", "dispatching", "running", "waiting_local", "completed", "failed", "cancelled")

RUN_TRANSITIONS: Dict[str, Dict[str, str]] = {
    "planning": {"PUBLISH": "dispatching", "FAIL": "failed", "CANCEL": "cancelled"},
    "dispatching": {"START": "running", "FAIL": "failed", "CANCEL": "cancelled"},
    "running": {"WAIT_LOCAL": "waiting_local", "COMPLETE": "completed", "FAIL": "failed", "CANCEL": "cancelled"},
    "waiting_local": {"RESUME": "running", "COMPLETE": "completed", "FAIL": "failed", "CANCEL": "cancelled"},
    "completed": {"REOPEN": "planning"},
    "failed": {"REOPEN": "planning"},
    "cancelled": {"REOPEN": "planning"},
}

RUN_EVENTS = frozenset(event for mapping in RUN_TRANSITIONS.values() for event in mapping)


def apply_transition(state: str, event: str) -> str:
    """Return the next task state for ``event`` or raise ``StateTransitionError``."""
    if state not in TASK_STATES:
        raise StateTransitionError("unknown task state %r" % (state,))
    allowed = TASK_TRANSITIONS.get(state, {})
    if event not in allowed:
        raise StateTransitionError("event %r is not allowed from state %r" % (event, state))
    return allowed[event]


def apply_run_transition(state: str, event: str) -> str:
    if state not in RUN_STATES:
        raise StateTransitionError("unknown run state %r" % (state,))
    allowed = RUN_TRANSITIONS.get(state, {})
    if event not in allowed:
        raise StateTransitionError("event %r is not allowed from run state %r" % (event, state))
    return allowed[event]
