from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import _bootstrap  # noqa: F401
from orchestrator.claims import claim_task, mark_paid_invocation, update_claim
from orchestrator.errors import ClaimConflictError, DuplicatePaidInvocationError, LiveInvocationBlockedError, ProtocolError
from orchestrator.worker import DeepSeekWorkerAdapter, FakeWorkerAdapter


TASK = {"task_id": "task-01", "objective": "Implement the bounded change."}


class CapturingTransport:
    def __init__(self):
        self.calls = []

    def invoke(self, endpoint, payload, api_key):
        self.calls.append((endpoint, payload, api_key))
        return {"id": "provider-01", "choices": [{"message": {"content": "done"}}]}


class EchoKeyTransport:
    def invoke(self, endpoint, payload, api_key):
        return {"id": "provider-echo", "choices": [{"message": {"content": "unexpected echo: " + api_key}}]}


class ClaimsAndWorkerTests(unittest.TestCase):
    def test_atomic_claim_and_paid_idempotency(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = claim_task(root, "task-01", "worker-a")
            second = claim_task(root, "task-01", "worker-a")
            self.assertEqual(first["claimed_at"], second["claimed_at"])
            with self.assertRaises(ClaimConflictError):
                claim_task(root, "task-01", "worker-b")
            mark_paid_invocation(root, "task-01", "provider-01")
            with self.assertRaises(DuplicatePaidInvocationError):
                mark_paid_invocation(root, "task-01", "provider-02")
            with self.assertRaises(ValueError):
                update_claim(root, "task-01", "completed")

    def test_fake_worker_never_invokes_network(self):
        result = FakeWorkerAdapter().run(TASK)
        self.assertTrue(result.dry_run)
        self.assertEqual(result.provider, "fake")

    def test_deepseek_requires_explicit_live_gate(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(LiveInvocationBlockedError):
                DeepSeekWorkerAdapter(CapturingTransport()).run(TASK, "unused")

    def test_injected_transport_exercises_paid_boundary_without_network(self):
        with tempfile.TemporaryDirectory() as temp:
            claim_task(Path(temp), "task-01", "deepseek")
            transport = CapturingTransport()
            env = {"RWR_ALLOW_LIVE": "1", "DEEPSEEK_API_KEY": "test-only-secret"}
            with patch.dict(os.environ, env, clear=True):
                result = DeepSeekWorkerAdapter(transport).run(TASK, temp)
            self.assertEqual(result.provider_run_id, "provider-01")
            self.assertEqual(len(transport.calls), 1)
            endpoint, payload, key = transport.calls[0]
            self.assertTrue(endpoint.endswith("/chat/completions"))
            self.assertEqual(key, "test-only-secret")
            self.assertNotIn(key, str(payload))
            self.assertEqual(payload["model"], "deepseek-v4-flash")
            self.assertEqual(payload["reasoning_effort"], "high")
            self.assertEqual(payload["thinking"], {"type": "enabled"})
            self.assertEqual(result.model, "deepseek-v4-flash")

    def test_deep_model_class_selects_pro_and_max_reasoning(self):
        with tempfile.TemporaryDirectory() as temp:
            claim_task(Path(temp), "task-02", "deepseek")
            transport = CapturingTransport()
            task = {**TASK, "task_id": "task-02", "worker": {"model_class": "deep", "role": "planner"}}
            env = {"RWR_ALLOW_LIVE": "1", "DEEPSEEK_API_KEY": "test-only-secret"}
            with patch.dict(os.environ, env, clear=True):
                result = DeepSeekWorkerAdapter(transport).run(task, temp)
            _, payload, _ = transport.calls[0]
            self.assertEqual(payload["model"], "deepseek-v4-pro")
            self.assertEqual(payload["reasoning_effort"], "max")
            self.assertIn("bounded architecture planner", payload["messages"][0]["content"])
            self.assertEqual(result.model, "deepseek-v4-pro")

    def test_planner_cannot_silently_fall_back_to_flash(self):
        with tempfile.TemporaryDirectory() as temp:
            claim_task(Path(temp), "task-04", "deepseek")
            task = {**TASK, "task_id": "task-04", "worker": {"model_class": "balanced", "role": "planner"}}
            env = {"RWR_ALLOW_LIVE": "1", "DEEPSEEK_API_KEY": "test-only-secret"}
            with patch.dict(os.environ, env, clear=True):
                with self.assertRaises(ProtocolError):
                    DeepSeekWorkerAdapter(CapturingTransport()).run(task, temp)
            mark_paid_invocation(Path(temp), "task-04", "provider-after-role-validation")

    def test_invalid_model_class_fails_before_paid_marker(self):
        with tempfile.TemporaryDirectory() as temp:
            claim_task(Path(temp), "task-03", "deepseek")
            task = {**TASK, "task_id": "task-03", "worker": {"model_class": "unknown"}}
            env = {"RWR_ALLOW_LIVE": "1", "DEEPSEEK_API_KEY": "test-only-secret"}
            with patch.dict(os.environ, env, clear=True):
                with self.assertRaises(ProtocolError):
                    DeepSeekWorkerAdapter(CapturingTransport()).run(task, temp)
            mark_paid_invocation(Path(temp), "task-03", "provider-after-validation")

    def test_provider_key_echo_is_redacted(self):
        with tempfile.TemporaryDirectory() as temp:
            claim_task(Path(temp), "task-01", "deepseek")
            env = {"RWR_ALLOW_LIVE": "1", "DEEPSEEK_API_KEY": "test-only-secret"}
            with patch.dict(os.environ, env, clear=True):
                result = DeepSeekWorkerAdapter(EchoKeyTransport()).run(TASK, temp)
            self.assertNotIn("test-only-secret", result.summary)


if __name__ == "__main__":
    unittest.main()
