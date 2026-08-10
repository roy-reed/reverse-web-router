"""Provider-neutral worker adapters with an explicit paid boundary."""
from __future__ import annotations

import json
import os
import urllib.request
import uuid
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Protocol

from .claims import mark_paid_invocation
from .errors import LiveInvocationBlockedError, MissingCredentialError
from .security import ensure_cloud_safe, redact


@dataclass
class WorkerResult:
    provider: str
    provider_run_id: str
    state: str
    summary: str
    dry_run: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Transport(Protocol):
    def invoke(self, endpoint: str, payload: Dict[str, Any], api_key: str) -> Dict[str, Any]: ...


class UrlLibResponsesTransport:
    """Minimal Responses-compatible HTTPS transport, used only after explicit enablement."""

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
            provider_run_id="dryrun-" + task["task_id"],
            state="completed",
            summary="Dry-run worker accepted the bounded task without an external invocation.",
            dry_run=True,
        )


class DeepSeekWorkerAdapter:
    provider = "deepseek"

    def __init__(self, transport: Optional[Transport] = None):
        self.transport = transport or UrlLibResponsesTransport()

    def run(self, task: Dict[str, Any], claim_dir: str) -> WorkerResult:
        ensure_cloud_safe(task)
        if os.environ.get("RWR_ALLOW_LIVE") != "1":
            raise LiveInvocationBlockedError("live worker requires RWR_ALLOW_LIVE=1")
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise MissingCredentialError("DEEPSEEK_API_KEY is required at runtime")

        provisional_id = "pending-" + str(uuid.uuid4())
        mark_paid_invocation(claim_dir, task["task_id"], provisional_id)
        endpoint = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/") + "/responses"
        payload = {
            "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash"),
            "input": json.dumps(redact(task), ensure_ascii=False),
            "stream": False,
        }
        response = self.transport.invoke(endpoint, payload, api_key)
        run_id = str(response.get("id") or provisional_id)
        summary = str(response.get("output_text") or "Provider response received; inspect the linked artifact.")
        summary = summary.replace(api_key, "[REDACTED]")
        return WorkerResult(self.provider, run_id, "completed", summary[:2000], False)
