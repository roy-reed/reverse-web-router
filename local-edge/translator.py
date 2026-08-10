"""Compatibility translation between LOCAL_EDGE rwrouter/1.1 and rwrouter/2."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

ORCHESTRATOR = Path(__file__).resolve().parents[1] / ".agent-orchestrator"
sys.path.insert(0, str(ORCHESTRATOR))

from orchestrator.errors import TranslationError  # noqa: E402
from orchestrator.routing import CANONICAL_TO_LEGACY, canonical_surface  # noqa: E402
from orchestrator.schema import validate_envelope  # noqa: E402
from orchestrator.security import ensure_cloud_safe, redact  # noqa: E402


def v11_to_v2(packet: Dict[str, Any]) -> Dict[str, Any]:
    if packet.get("protocol") != "rwrouter/1.1":
        raise TranslationError("LOCAL_EDGE accepts only rwrouter/1.1 input")
    surface = canonical_surface(packet.get("execution_surface"))
    envelope: Dict[str, Any] = {
        "protocol": "rwrouter/2",
        "task_id": packet.get("task_id"),
        "surface": surface,
        "web_capability": packet.get("web_capability", "FAST"),
        "objective": packet.get("objective", ""),
        "context": packet.get("context", {}),
        "constraints": packet.get("constraints", []),
        "acceptance_criteria": {
            "definition_of_done": packet.get("acceptance_checks") or ["Return a verified receipt"],
            "commands": [],
        },
        "orchestration": {
            "mode": "SINGLE_AGENT",
            "planner": "WEB",
            "worker_policy": "AUTO",
            "merge_policy": "NO_MAIN_AUTO_MERGE",
        },
    }
    project = {}
    if packet.get("workspace_alias"):
        project["workspace_alias"] = packet["workspace_alias"]
    if project:
        envelope["project"] = project
    if surface in ("LOCAL_EDGE", "HYBRID_CLOUD_LOCAL"):
        envelope["edge"] = {
            "local_backend_preference": packet.get("local_backend_preference", "AUTO"),
            "local_capability": packet.get("local_capability", "BALANCED"),
            "task_kind": packet.get("task_kind", "other"),
            "execution_policy": packet.get("execution_policy", "SAFE_WORKSPACE"),
            "network_policy": packet.get("network_policy", "OFF"),
            "return_mode": packet.get("return_mode", "SUMMARY_AND_RECEIPT"),
        }
    ensure_cloud_safe(envelope)
    errors = validate_envelope(envelope)
    if errors:
        raise TranslationError("invalid translated envelope: " + "; ".join(errors))
    return envelope


def v2_to_v11(envelope: Dict[str, Any]) -> Dict[str, Any]:
    if envelope.get("protocol") != "rwrouter/2":
        raise TranslationError("expected rwrouter/2")
    surface = canonical_surface(envelope.get("surface"))
    if surface not in CANONICAL_TO_LEGACY:
        raise TranslationError("surface %s has no LOCAL_EDGE wire representation" % surface)
    edge = envelope.get("edge") or {}
    project = envelope.get("project") or {}
    packet = {
        "protocol": "rwrouter/1.1",
        "task_id": envelope["task_id"],
        "execution_surface": CANONICAL_TO_LEGACY[surface],
        "web_capability": envelope.get("web_capability", "FAST"),
        "local_backend_preference": edge.get("local_backend_preference", "AUTO"),
        "local_capability": edge.get("local_capability", "BALANCED"),
        "task_kind": edge.get("task_kind", "other"),
        "workspace_alias": project.get("workspace_alias", "default"),
        "execution_policy": "SAFE_WORKSPACE",
        "network_policy": "OFF",
        "objective": envelope.get("objective", ""),
        "context": envelope.get("context", {}),
        "constraints": envelope.get("constraints", []),
        "acceptance_checks": (envelope.get("acceptance_criteria") or {}).get("definition_of_done", []),
        "return_mode": edge.get("return_mode", "SUMMARY_AND_RECEIPT"),
    }
    ensure_cloud_safe(packet)
    return packet


def sanitized_receipt(task_id: str, state: str, backend: str, summary: str) -> Dict[str, Any]:
    return redact({
        "protocol": "rwrouter/1.1",
        "task_id": task_id,
        "state": state,
        "local_backend_selected": backend,
        "summary": summary,
        "errors": [],
    })


if __name__ == "__main__":
    print(json.dumps(v11_to_v2(json.load(sys.stdin)), ensure_ascii=False, indent=2))
