"""Provider-neutral worker adapters with an explicit paid boundary."""
from __future__ import annotations

import json
import os
import urllib.request
import uuid
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Protocol

from .claims import mark_paid_invocation
from .errors import LiveInvocationBlockedError, MissingCredentialError, ProtocolError
from .security import ensure_cloud_safe, redact

MODEL_BY_CLASS = {
    "fast": "deepseek-v4-flash",
    "balanced": "deepseek-v4-flash",
    "deep": "deepseek-v4-pro",
}

ROLE_PROMPTS = {
    "planner": (
        "Act as a bounded architecture planner. Return a decomposition, module boundaries, risks, "
        "and deterministic acceptance criteria. Do not implement files or expand the supplied scope."
    ),
    "implementer": (
        "Act as a bounded implementation worker. Change only allowed paths and satisfy the frozen "
        "acceptance criteria. Do not broaden the objective or invent credentials."
    ),
    "verifier": (
        "Act as an evidence-bounded verifier. Evaluate each acceptance criterion as pass, fail, or "
        "unknown and cite only supplied artifacts. Do not modify the implementation."
    ),
    "reviewer": (
        "Act as a bounded architecture and code reviewer. Report only actionable defects, their "
        "impact, evidence, and the smallest repair. Do not redesign unrelated components."
    ),
}


@dataclass
class WorkerResult:
    provider: str
    model: str
    provider_run_id: str
    state: str
    summary: str
    dry_run: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Transport(Protocol):
    def invoke(self, endpoint: str, payload: Dict[str, Any], api_key: str) -> Dict[str, Any]: ...


class UrlLibChatCompletionsTransport:
    """Minimal Chat Completions HTTPS transport, used only after explicit enablement."""

    def invoke(self, endpoint: str, payload: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=900) as response:
            return json.loads(response.read().decode("utf-8"))


class FakeWorkerAdapter:
    provider = "fake"

    def run(self, task: Dict[str, Any]) -> WorkerResult:
        ensure_cloud_safe(task)
        return WorkerResult(
            provider=self.provider,
            model="fake",
            provider_run_id="dryrun-" + task["task_id"],
            state="completed",
            summary="Dry-run worker accepted the bounded task without an external invocation.",
            dry_run=True,
        )


class DeepSeekWorkerAdapter:
    provider = "deepseek"

    def __init__(self, transport: Optional[Transport] = None):
        self.transport = transport or UrlLibChatCompletionsTransport()

    @staticmethod
    def select_model(task: Dict[str, Any]) -> tuple[str, str]:
        model_class = str(task.get("worker", {}).get("model_class", "balanced"))
        if model_class not in MODEL_BY_CLASS:
            raise ProtocolError("worker.model_class must be fast, balanced, or deep")
        model = MODEL_BY_CLASS[model_class]
        override = os.environ.get("RWR_DEEPSEEK_MODEL_OVERRIDE")
        if override:
            if override not in set(MODEL_BY_CLASS.values()):
                raise ProtocolError("RWR_DEEPSEEK_MODEL_OVERRIDE is not an approved DeepSeek V4 model")
            model = override
        return model_class, model

    @staticmethod
    def select_role(task: Dict[str, Any], model_class: str) -> str:
        role = str(task.get("worker", {}).get("role", "implementer"))
        if role not in ROLE_PROMPTS:
            raise ProtocolError("worker.role must be planner, implementer, verifier, or reviewer")
        if role in ("planner", "reviewer") and model_class != "deep":
            raise ProtocolError("planner and reviewer roles require worker.model_class=deep")
        return role

    def run(self, task: Dict[str, Any], claim_dir: str) -> WorkerResult:
        ensure_cloud_safe(task)
        if os.environ.get("RWR_ALLOW_LIVE") != "1":
            raise LiveInvocationBlockedError("live worker requires RWR_ALLOW_LIVE=1")
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise MissingCredentialError("DEEPSEEK_API_KEY is required at runtime")

        model_class, model = self.select_model(task)
        role = self.select_role(task, model_class)
        provisional_id = "pending-" + str(uuid.uuid4())
        mark_paid_invocation(claim_dir, task["task_id"], provisional_id)
        endpoint = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/") + "/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": ROLE_PROMPTS[role]},
                {"role": "user", "content": json.dumps(redact(task), ensure_ascii=False)}
            ],
            "stream": False,
            "thinking": {"type": "enabled"},
            "reasoning_effort": "max" if model_class == "deep" else "high",
        }
        response = self.transport.invoke(endpoint, payload, api_key)
        run_id = str(response.get("id") or provisional_id)
        choices = response.get("choices") or []
        message = choices[0].get("message", {}) if choices and isinstance(choices[0], dict) else {}
        summary = str(message.get("content") or "Provider response received; inspect the linked artifact.")
        summary = summary.replace(api_key, "[REDACTED]")
        return WorkerResult(self.provider, model, run_id, "completed", summary[:2000], False)
