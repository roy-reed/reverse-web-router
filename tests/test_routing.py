from __future__ import annotations

import unittest

import _bootstrap  # noqa: F401
from orchestrator.errors import ProtocolError
from orchestrator.routing import SURFACES, build_envelope, canonical_surface, classify, plan_reasoning


class RoutingTests(unittest.TestCase):
    def test_canonical_surface_set_is_exact(self):
        self.assertEqual(
            set(SURFACES),
            {"CONTROL", "WEB_DIRECT", "GITHUB_CLOUD", "LOCAL_EDGE", "HYBRID_CLOUD_LOCAL"},
        )

    def test_legacy_mapping_exists_only_at_explicit_boundary(self):
        self.assertEqual(canonical_surface("WEB"), "WEB_DIRECT")
        self.assertEqual(canonical_surface("LOCAL"), "LOCAL_EDGE")
        self.assertEqual(canonical_surface("HYBRID"), "HYBRID_CLOUD_LOCAL")
        with self.assertRaises(ProtocolError):
            canonical_surface("UNKNOWN")

    def test_classifier_prefers_cloud_for_repo_engineering(self):
        self.assertEqual(classify({"repository": True}), "GITHUB_CLOUD")
        self.assertEqual(
            classify({"repository": True, "requires_local_acceptance": True}),
            "HYBRID_CLOUD_LOCAL",
        )
        self.assertEqual(classify({"requires_local": True}), "LOCAL_EDGE")
        self.assertEqual(classify({"web_only": True}), "WEB_DIRECT")
        self.assertEqual(classify({"control": True, "repository": True}), "CONTROL")

    def test_reasoning_and_execution_are_independent_axes(self):
        web_only = plan_reasoning({"web_only": True, "complexity_score": 9})
        self.assertEqual(web_only["web_tier"], "DEEP")
        self.assertEqual(web_only["delegated_stage"], "NONE")
        self.assertEqual(web_only["execution_tier"], "NONE")
        self.assertEqual(web_only["execution_role"], "NONE")
        self.assertEqual(web_only["execution_effort"], "NONE")

        repo = plan_reasoning({"repository": True, "complexity_score": 7})
        self.assertEqual(repo["web_tier"], "DEEP")
        self.assertEqual(repo["delegated_stage"], "NONE")
        self.assertEqual(repo["execution_tier"], "BALANCED")
        self.assertEqual(repo["execution_role"], "TERRA")
        self.assertEqual(repo["execution_effort"], "XHIGH")
        self.assertEqual(repo["max_external_reasoning_calls"], 0)

    def test_explicit_planner_delegation_has_one_external_call(self):
        plan = plan_reasoning({
            "repository": True,
            "complexity_score": 7,
            "delegated_stage": "PLANNER",
        })
        self.assertEqual(plan["delegated_stage"], "PLANNER")
        self.assertEqual(plan["max_external_reasoning_calls"], 1)

    def test_auto_delegation_remains_off_even_for_hard_tasks(self):
        plan = plan_reasoning({
            "repository": True,
            "complexity_score": 10,
            "risk": "HIGH",
            "delegated_stage": "AUTO",
        })
        self.assertEqual(plan["execution_tier"], "DEEP")
        self.assertEqual(plan["delegated_stage"], "NONE")
        self.assertEqual(plan["max_external_reasoning_calls"], 0)

    def test_local_capability_tier_boundaries(self):
        expected = {
            0: ("FAST", "LUNA", "NONE"),
            1: ("FAST", "LUNA", "LOW"),
            2: ("FAST", "LUNA", "LOW"),
            3: ("FAST", "LUNA", "MEDIUM"),
            4: ("FAST", "LUNA", "MEDIUM"),
            5: ("FAST", "LUNA", "HIGH"),
            6: ("BALANCED", "TERRA", "HIGH"),
            7: ("BALANCED", "TERRA", "XHIGH"),
            8: ("DEEP", "SOL", "MAX"),
            10: ("DEEP", "SOL", "MAX"),
        }
        for score, target in expected.items():
            with self.subTest(score=score):
                plan = plan_reasoning({
                    "repository": True,
                    "complexity_score": score,
                })
                self.assertEqual(
                    (plan["execution_tier"], plan["execution_role"], plan["execution_effort"]),
                    target,
                )

    def test_control_is_the_only_non_sol_web_gateway(self):
        control = plan_reasoning({"control": True, "complexity_score": 10})
        substantive = plan_reasoning({"repository": True, "complexity_score": 0})
        self.assertEqual(control["web_tier"], "FAST")
        self.assertEqual(substantive["web_tier"], "DEEP")

    def test_dual_deep_stage_requires_high_risk_and_opt_in(self):
        with self.assertRaises(ProtocolError):
            plan_reasoning({"repository": True, "complexity_score": 9, "delegated_stage": "PLANNER_AND_REVIEWER"})
        plan = plan_reasoning({
            "repository": True,
            "complexity_score": 9,
            "risk": "HIGH",
            "delegated_stage": "PLANNER_AND_REVIEWER",
            "allow_dual_deep": True,
        })
        self.assertEqual(plan["max_external_reasoning_calls"], 2)

    def test_envelope_records_acceptance_authority(self):
        envelope = build_envelope({
            "repository": True,
            "requires_local_acceptance": True,
            "complexity_score": 8,
            "objective": "Implement and validate the bounded change locally.",
        })
        self.assertEqual(envelope["surface"], "HYBRID_CLOUD_LOCAL")
        self.assertEqual(envelope["reasoning_plan"]["acceptance_authority"], "LOCAL_CODEX")


if __name__ == "__main__":
    unittest.main()
