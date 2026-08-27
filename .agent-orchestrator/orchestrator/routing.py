"""Canonical routing surfaces and the legacy rwrouter/1.1 mapping.

Canonical surfaces (rwrouter/2):

- ``CONTROL``              acknowledgements, approvals, status requests.
- ``WEB_DIRECT``           web-only analysis/writing/research.
- ``GITHUB_CLOUD``         repository engineering on GitHub infrastructure.
- ``LOCAL_EDGE``           local-only work via the V2 edge chain.
- ``HYBRID_CLOUD_LOCAL``   cloud-safe stages plus explicit local acceptance.

Legacy rwrouter/1.1 values are accepted only through :func:`canonical_surface`
at the LOCAL_EDGE boundary: WEB -> WEB_DIRECT, LOCAL -> LOCAL_EDGE,
HYBRID -> HYBRID_CLOUD_LOCAL.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .errors import ProtocolError

SURFACES = (
    "CONTROL",
    "WEB_DIRECT",
    "GITHUB_CLOUD",
    "LOCAL_EDGE",
    "HYBRID_CLOUD_LOCAL",
)

LEGACY_SURFACE_MAP = {
    "WEB": "WEB_DIRECT",
    "LOCAL": "LOCAL_EDGE",
    "HYBRID": "HYBRID_CLOUD_LOCAL",
}

CANONICAL_TO_LEGACY = {v: k for k, v in LEGACY_SURFACE_MAP.items()}

WEB_CAPABILITIES = ("FAST", "BALANCED", "DEEP")

DELEGATED_STAGES = ("NONE", "PLANNER", "REVIEWER", "PLANNER_AND_REVIEWER")

ACCEPTANCE_AUTHORITIES = ("WEB", "LOCAL_CODEX", "GITHUB_CHECKS", "USER")

TASK_KINDS = ("coding", "file_ops", "analysis", "artifact", "research", "system", "other")

LOCAL_BACKEND_PREFERENCES = ("AUTO", "CODEX_DIRECT", "CODING_RUNNER")

WORKER_POLICIES = ("AUTO", "MANUAL")

MERGE_POLICIES = ("NO_MAIN_AUTO_MERGE", "ALLOW_INTEGRATION_BRANCH")

ORCHESTRATION_MODES = ("SINGLE_AGENT", "MULTI_AGENT")

PLANNERS = ("WEB", "CODE", "HUMAN")


def canonical_surface(value: Optional[str]) -> str:
    """Map a legacy or canonical surface value to its canonical form.

    Unknown values raise ``ProtocolError`` (fail closed).
    """
    if value is None:
        raise ProtocolError("missing routing surface")
    v = value.strip().upper()
    v = LEGACY_SURFACE_MAP.get(v, v)
    if v not in SURFACES:
        raise ProtocolError("unknown routing surface %r (canonical: %s)" % (value, ", ".join(SURFACES)))
    return v


def is_canonical_surface(value: Optional[str]) -> bool:
    try:
        canonical_surface(value)
        return True
    except ProtocolError:
        return False


def classify(request: Dict[str, Any]) -> str:
    """Deterministic routing decision used by the web planner.

    Keys understood:

    - ``control``                     acknowledgement/status/approval traffic;
    - ``web_only``                    no repository or local execution needed;
    - ``repository``                  repository-based work;
    - ``requires_local``              materially depends on local resources;
    - ``requires_local_acceptance``   needs an explicit local acceptance stage.
    """
    if request.get("control"):
        return "CONTROL"
    repository = bool(request.get("repository"))
    requires_local = bool(request.get("requires_local"))
    local_acceptance = bool(request.get("requires_local_acceptance"))
    web_only = bool(request.get("web_only"))
    if web_only or not repository:
        return "LOCAL_EDGE" if requires_local else "WEB_DIRECT"
    if local_acceptance:
        return "HYBRID_CLOUD_LOCAL"
    if requires_local:
        return "LOCAL_EDGE"
    return "GITHUB_CLOUD"


def plan_reasoning(request: Dict[str, Any], surface: Optional[str] = None) -> Dict[str, Any]:
    """Plan reasoning separately from the execution surface.

    ``rwrouter/2`` stays provider-neutral: adapters decide which concrete model
    implements a delegated deep stage.  The default budget permits at most one
    such stage.  A planner+reviewer pair is allowed only when the request marks
    the work high impact and explicitly opts into the second paid stage.
    """
    selected_surface = surface or classify(request)
    try:
        score = int(request.get("complexity_score", 4))
    except (TypeError, ValueError) as exc:
        raise ProtocolError("complexity_score must be an integer from 0 to 10") from exc
    if not 0 <= score <= 10:
        raise ProtocolError("complexity_score must be an integer from 0 to 10")

    risk = str(request.get("risk", "MEDIUM")).upper()
    if risk not in ("LOW", "MEDIUM", "HIGH"):
        raise ProtocolError("risk must be LOW, MEDIUM, or HIGH")

    # Substantive web-originated work always passes the Sol High gateway.
    # CONTROL remains a zero-handoff acknowledgement/status path.
    web_tier = "FAST" if selected_surface == "CONTROL" else "DEEP"
    execution_tier = "NONE"
    execution_role = "NONE"
    execution_effort = "NONE"
    if selected_surface in ("GITHUB_CLOUD", "LOCAL_EDGE", "HYBRID_CLOUD_LOCAL"):
        # Logical local roles: FAST=Luna, BALANCED=Terra, DEEP=Sol.
        # Provider-native model names remain in adapters, not the envelope.
        execution_tier = "FAST" if score <= 5 else "BALANCED" if score <= 7 else "DEEP"
        if score == 0:
            execution_role, execution_effort = "LUNA", "NONE"
        elif score <= 2:
            execution_role, execution_effort = "LUNA", "LOW"
        elif score <= 4:
            execution_role, execution_effort = "LUNA", "MEDIUM"
        elif score == 5:
            execution_role, execution_effort = "LUNA", "HIGH"
        elif score == 6:
            execution_role, execution_effort = "TERRA", "HIGH"
        elif score == 7:
            execution_role, execution_effort = "TERRA", "XHIGH"
        else:
            execution_role, execution_effort = "SOL", "MAX"

    requested_stage = str(request.get("delegated_stage", "AUTO")).upper()
    if requested_stage == "AUTO":
        # AUTO is deliberately default-off. Spending an external-provider budget
        # requires an explicit PLANNER, REVIEWER, or PLANNER_AND_REVIEWER request.
        delegated_stage = "NONE"
    else:
        delegated_stage = requested_stage
    if delegated_stage not in DELEGATED_STAGES:
        raise ProtocolError("delegated_stage must be AUTO, NONE, PLANNER, REVIEWER, or PLANNER_AND_REVIEWER")

    allow_dual = bool(request.get("allow_dual_deep"))
    if delegated_stage == "PLANNER_AND_REVIEWER" and not (risk == "HIGH" and allow_dual):
        raise ProtocolError("planner+reviewer requires risk HIGH and allow_dual_deep=true")
    max_external_calls = 2 if delegated_stage == "PLANNER_AND_REVIEWER" else int(delegated_stage != "NONE")

    if request.get("requires_user_decision"):
        acceptance_authority = "USER"
    elif selected_surface in ("LOCAL_EDGE", "HYBRID_CLOUD_LOCAL"):
        acceptance_authority = "LOCAL_CODEX"
    elif selected_surface == "GITHUB_CLOUD":
        acceptance_authority = "GITHUB_CHECKS"
    else:
        acceptance_authority = "WEB"

    return {
        "complexity_score": score,
        "risk": risk,
        "web_tier": web_tier,
        "delegated_stage": delegated_stage,
        "execution_tier": execution_tier,
        "execution_role": execution_role,
        "execution_effort": execution_effort,
        "max_external_reasoning_calls": max_external_calls,
        "supervisor": "WEB",
        "acceptance_authority": acceptance_authority,
    }


def build_envelope(request: Dict[str, Any], task_id: Optional[str] = None) -> Dict[str, Any]:
    """Build a minimal rwrouter/2 semantic envelope from a routing request."""
    from . import yamlmini  # noqa: F401  (kept for parity; envelope is JSON-safe)

    surface = classify(request)
    reasoning_plan = plan_reasoning(request, surface)
    envelope = {
        "protocol": "rwrouter/2",
        "task_id": task_id or _new_uuid(),
        "surface": surface,
        "web_capability": request.get("web_capability", reasoning_plan["web_tier"]),
        "objective": request.get("objective", ""),
        "reasoning_plan": reasoning_plan,
    }
    repository_alias = request.get("repository_alias")
    workspace_alias = request.get("workspace_alias")
    project = {}
    if repository_alias:
        project["repository_alias"] = repository_alias
    if workspace_alias:
        project["workspace_alias"] = workspace_alias
    if project:
        envelope["project"] = project
    if surface in ("LOCAL_EDGE", "HYBRID_CLOUD_LOCAL"):
        envelope["edge"] = {
            "local_backend_preference": request.get("local_backend_preference", "AUTO"),
            "local_capability": request.get("local_capability", "BALANCED"),
            "task_kind": request.get("task_kind", "coding"),
            "execution_policy": "SAFE_WORKSPACE",
            "network_policy": "OFF",
            "return_mode": request.get("return_mode", "SUMMARY_AND_RECEIPT"),
        }
    envelope["orchestration"] = {
        "mode": request.get("orchestration_mode", "MULTI_AGENT" if surface == "GITHUB_CLOUD" else "SINGLE_AGENT"),
        "planner": "WEB",
        "worker_policy": request.get("worker_policy", "AUTO"),
        "merge_policy": "NO_MAIN_AUTO_MERGE",
    }
    return envelope


def _new_uuid() -> str:
    import uuid

    return str(uuid.uuid4())
