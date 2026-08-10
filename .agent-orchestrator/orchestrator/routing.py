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


def build_envelope(request: Dict[str, Any], task_id: Optional[str] = None) -> Dict[str, Any]:
    """Build a minimal rwrouter/2 semantic envelope from a routing request."""
    from . import yamlmini  # noqa: F401  (kept for parity; envelope is JSON-safe)

    surface = classify(request)
    envelope = {
        "protocol": "rwrouter/2",
        "task_id": task_id or _new_uuid(),
        "surface": surface,
        "web_capability": request.get("web_capability", "BALANCED"),
        "objective": request.get("objective", ""),
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
