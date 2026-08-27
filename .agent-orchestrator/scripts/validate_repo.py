#!/usr/bin/env python3
"""Fail-closed repository validation for the reverse-web-router MVP."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATOR_ROOT = ROOT / ".agent-orchestrator"
sys.path.insert(0, str(ORCHESTRATOR_ROOT))

from orchestrator.routing import SURFACES  # noqa: E402
from orchestrator.schema import load_schema, validate_envelope, validate_work_unit  # noqa: E402
from orchestrator.yamlmini import parse as parse_yaml  # noqa: E402


REQUIRED_FILES = (
    "LICENSE",
    "README.md",
    "ARCHITECTURE_DECISION.md",
    "PROTOCOL.md",
    "pyproject.toml",
    ".agent-orchestrator/config.yml",
    ".agent-orchestrator/schema/rwrouter2.schema.json",
    ".agent-orchestrator/schema/run.schema.json",
    ".agent-orchestrator/schema/work-unit.schema.json",
    ".agent-orchestrator/schema/worker-selection.schema.json",
    ".agent-orchestrator/schema/dependency-state.schema.json",
    ".agent-orchestrator/schema/budget.schema.json",
    ".github/workflows/agent-dispatch.yml",
    ".github/workflows/agent-verify.yml",
    ".github/workflows/agent-integrate.yml",
    "web-project/PROJECT_INSTRUCTIONS.md",
    "web-project/USER_WEB_SETUP.md",
    "docs/web-local-reasoning-routing.md",
    "local-edge/translator.py",
    "local-edge/bridge/native_host.py",
    "local-edge/extension/manifest.json",
    "local-edge/LOCAL_EDGE_SETUP.md",
    "codex-skill/reverse-web-router-executor/SKILL.md",
    "codex-skill/reverse-web-router-executor/agents/openai.yaml",
)

SCHEMA_NAMES = (
    "rwrouter2.schema.json",
    "run.schema.json",
    "work-unit.schema.json",
    "worker-selection.schema.json",
    "dependency-state.schema.json",
    "budget.schema.json",
)

WORKFLOWS = (
    ".github/workflows/agent-dispatch.yml",
    ".github/workflows/agent-verify.yml",
    ".github/workflows/agent-integrate.yml",
)

FORBIDDEN_WORKFLOW_TEXT = (
    "pull_request_target",
    "git push --force",
    "git push origin main",
    "gh pr merge",
    "merge main",
    "permissions: write-all",
)


def sample_work_unit() -> dict:
    return {
        "schema": "agent-task/v1",
        "task_id": "task-01",
        "run_id": "run-01",
        "objective": "Implement one bounded and independently verifiable unit.",
        "depends_on": [],
        "worker": {"provider": "fake", "model_class": "fast", "role": "implementer"},
        "allowed_paths": ["src/**"],
        "forbidden_paths": [".git/**"],
        "definition_of_done": ["Unit tests pass"],
        "acceptance_commands": ["python -m unittest"],
        "budget": {"max_wall_minutes": 10, "max_cost_usd": 0},
        "state": "ready",
    }


def sample_envelope() -> dict:
    return {
        "protocol": "rwrouter/2",
        "task_id": "00000000-0000-4000-8000-000000000001",
        "surface": "GITHUB_CLOUD",
        "web_capability": "BALANCED",
        "objective": "Implement the bounded repository task.",
        "orchestration": {
            "mode": "MULTI_AGENT",
            "planner": "WEB",
            "worker_policy": "AUTO",
            "merge_policy": "NO_MAIN_AUTO_MERGE",
        },
    }


def validate_repository(root: Path = ROOT) -> list[str]:
    errors: list[str] = []

    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            errors.append("missing required file: " + relative)

    for name in SCHEMA_NAMES:
        try:
            schema = load_schema(name)
            if not isinstance(schema, dict):
                errors.append("schema is not an object: " + name)
        except Exception as exc:
            errors.append("cannot load schema %s: %s" % (name, exc))

    for relative in WORKFLOWS:
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        try:
            parsed = parse_yaml(text)
            if not isinstance(parsed, dict):
                errors.append("workflow root is not a mapping: " + relative)
        except Exception as exc:
            errors.append("invalid workflow YAML %s: %s" % (relative, exc))
        lowered = text.lower()
        for token in FORBIDDEN_WORKFLOW_TEXT:
            if token in lowered:
                errors.append("forbidden workflow operation %r in %s" % (token, relative))
        if "pull-requests: write" in text and "pull_request" not in text:
            errors.append("workflow requests pull-request write permission without a pull-request trigger: " + relative)

    dispatch_path = root / ".github/workflows/agent-dispatch.yml"
    if dispatch_path.is_file():
        dispatch = dispatch_path.read_text(encoding="utf-8")
        for required in (
            "issues:",
            "concurrency:",
            "permissions:",
            "contents: read",
            "github_ledger.py",
            "dependency_gate.py",
            "mark-paid",
            "finalize",
        ):
            if required not in dispatch:
                errors.append("dispatch workflow lacks %r" % required)
        if "pull-requests: write" in dispatch:
            errors.append("dispatch workflow requests unused pull-request write permission")

    project_path = root / "web-project/PROJECT_INSTRUCTIONS.md"
    if project_path.is_file():
        project_text = project_path.read_text(encoding="utf-8")
        for surface in SURFACES:
            if surface not in project_text:
                errors.append("project instructions omit surface " + surface)
        if "GITHUB_CLOUD" not in project_text or not (
            "default" in project_text.lower() or "默认" in project_text
        ):
            errors.append("project instructions do not state the GITHUB_CLOUD default")

    host_path = root / "local-edge/bridge/native_host.py"
    if host_path.is_file():
        host_text = host_path.read_text(encoding="utf-8").lower()
        for token in ("import socket", "httpserver", ".listen("):
            if token in host_text:
                errors.append("native host contains a network-listener primitive: " + token)

    manifest_path = root / "local-edge/extension/manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("manifest_version") != 3:
                errors.append("LOCAL_EDGE extension must use Manifest V3")
            permissions = set(manifest.get("permissions") or [])
            expected = {"activeTab", "storage", "nativeMessaging"}
            if permissions != expected:
                errors.append("extension permissions differ from the minimal reviewed set")
            if manifest.get("host_permissions") != ["https://chatgpt.com/*"]:
                errors.append("extension host permissions must be limited to chatgpt.com")
        except Exception as exc:
            errors.append("invalid extension manifest: " + str(exc))

    work_unit = sample_work_unit()
    errors.extend("sample work unit: " + item for item in validate_work_unit(work_unit))
    errors.extend("sample envelope: " + item for item in validate_envelope(sample_envelope()))

    # Nested worker and budget contracts are separately validated by entrypoints.
    from orchestrator.schema import validate_budget, validate_worker_selection

    errors.extend("sample worker: " + item for item in validate_worker_selection(work_unit["worker"]))
    errors.extend("sample budget: " + item for item in validate_budget(work_unit["budget"]))
    return errors


def main() -> int:
    errors = validate_repository()
    if errors:
        print("Repository validation failed:", file=sys.stderr)
        for error in errors:
            print("- " + error, file=sys.stderr)
        return 1
    print("Repository validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
