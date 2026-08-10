from __future__ import annotations

import unittest

import _bootstrap  # noqa: F401
from orchestrator.routing import build_envelope
from orchestrator.schema import validate_envelope, validate_work_unit


def valid_work_unit() -> dict:
    return {
        "schema": "agent-task/v1",
        "task_id": "task-01",
        "run_id": "run-01",
        "objective": "Implement a bounded, deterministic repository change.",
        "depends_on": [],
        "worker": {"provider": "fake", "model_class": "fast", "role": "implementer"},
        "allowed_paths": ["src/**"],
        "forbidden_paths": [".git/**"],
        "definition_of_done": ["Tests pass"],
        "acceptance_commands": ["python -m unittest"],
        "budget": {"max_wall_minutes": 10, "max_cost_usd": 0},
        "state": "ready",
    }


class SchemaTests(unittest.TestCase):
    def test_valid_work_unit(self):
        self.assertEqual(validate_work_unit(valid_work_unit()), [])

    def test_nested_worker_and_budget_fail_closed(self):
        bad = valid_work_unit()
        bad["worker"]["provider"] = "unlisted-provider"
        bad["budget"]["max_tokens"] = 0
        errors = validate_work_unit(bad)
        self.assertTrue(any("$.worker.provider" in item for item in errors))
        self.assertTrue(any("$.budget.max_tokens" in item for item in errors))

    def test_unknown_enum_and_property_fail_closed(self):
        bad = valid_work_unit()
        bad["state"] = "mystery"
        bad["surprise"] = True
        errors = validate_work_unit(bad)
        self.assertTrue(any("enum" in item for item in errors))
        self.assertTrue(any("unexpected property" in item for item in errors))

    def test_valid_rwrouter2_envelope(self):
        envelope = build_envelope(
            {"repository": True, "objective": "Implement a bounded repository change."},
            task_id="00000000-0000-4000-8000-000000000001",
        )
        self.assertEqual(validate_envelope(envelope), [])

    def test_unknown_surface_fails(self):
        envelope = build_envelope(
            {"repository": True, "objective": "Implement a bounded repository change."},
            task_id="00000000-0000-4000-8000-000000000001",
        )
        envelope["surface"] = "REMOTE_MAGIC"
        self.assertTrue(validate_envelope(envelope))


if __name__ == "__main__":
    unittest.main()
