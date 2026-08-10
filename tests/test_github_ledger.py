from __future__ import annotations

import json
import unittest

import _bootstrap  # noqa: F401
from orchestrator.errors import ClaimConflictError, DuplicatePaidInvocationError
from orchestrator.github_ledger import (
    extract_task_contract,
    find_ledger,
    parse_ledger,
    prepare_claim,
    prepare_paid,
    prepare_result,
    render_ledger,
)


class GitHubLedgerTests(unittest.TestCase):
    def test_claim_paid_and_duplicate_paid_gate(self):
        record, dispatchable = prepare_claim(None, "task-01", "deepseek")
        self.assertTrue(dispatchable)
        paid = prepare_paid(record, "pending-01")
        self.assertTrue(paid["paid_invoked"])
        self.assertEqual(paid["state"], "running")
        with self.assertRaises(DuplicatePaidInvocationError):
            prepare_paid(paid, "pending-02")
        repeated, dispatchable = prepare_claim(paid, "task-01", "deepseek")
        self.assertFalse(dispatchable)
        self.assertEqual(repeated["provider_run_id"], "pending-01")

    def test_ledger_round_trip_and_single_comment_invariant(self):
        record, _ = prepare_claim(None, "task-01", "fake")
        body = render_ledger(record)
        self.assertEqual(parse_ledger(body)["task_id"], "task-01")
        comment_id, found = find_ledger([{"id": 7, "body": body}], "task-01")
        self.assertEqual(comment_id, 7)
        self.assertEqual(found["state"], "claimed")
        with self.assertRaises(ClaimConflictError):
            find_ledger([{"id": 7, "body": body}, {"id": 8, "body": body}], "task-01")

    def test_result_maps_to_canonical_state(self):
        record, _ = prepare_claim(None, "task-01", "fake")
        success = prepare_result(record, {
            "result": {"provider_run_id": "dryrun-01", "summary": "done"},
            "errors": [],
        })
        self.assertEqual(success["state"], "verifying")
        failure = prepare_result(record, {"result": None, "errors": ["boom"]})
        self.assertEqual(failure["state"], "failed")

    def test_extracts_exact_task_contract(self):
        contract = {"schema": "agent-task/v1", "task_id": "task-01"}
        body = "```json\n%s\n```" % json.dumps(contract)
        self.assertEqual(extract_task_contract(body), contract)


if __name__ == "__main__":
    unittest.main()
