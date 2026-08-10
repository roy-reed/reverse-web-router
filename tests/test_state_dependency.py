from __future__ import annotations

import unittest

import _bootstrap  # noqa: F401
from orchestrator.dependency import check_dependencies, gate_dispatchable
from orchestrator.errors import StateTransitionError
from orchestrator.state import apply_run_transition, apply_transition


class StateAndDependencyTests(unittest.TestCase):
    def test_valid_and_invalid_transitions(self):
        self.assertEqual(apply_transition("ready", "CLAIM"), "claimed")
        self.assertEqual(apply_run_transition("running", "WAIT_LOCAL"), "waiting_local")
        with self.assertRaises(StateTransitionError):
            apply_transition("accepted", "START")

    def test_dependency_gate_requires_accepted(self):
        task = {"depends_on": ["a", "b", "c"]}
        result = check_dependencies(task, {"a": "accepted", "b": "running", "c": "failed"})
        self.assertFalse(result.ready)
        self.assertEqual(result.unsatisfied, [("b", "running")])
        self.assertEqual(result.failed, [("c", "failed")])

    def test_missing_dependency_and_claim_block(self):
        ready, reasons = gate_dispatchable({"depends_on": ["missing"]}, {}, claim_ok=False)
        self.assertFalse(ready)
        self.assertEqual(len(reasons), 2)


if __name__ == "__main__":
    unittest.main()
