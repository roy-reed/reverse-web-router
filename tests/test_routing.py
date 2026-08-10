from __future__ import annotations

import unittest

import _bootstrap  # noqa: F401
from orchestrator.errors import ProtocolError
from orchestrator.routing import SURFACES, canonical_surface, classify


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


if __name__ == "__main__":
    unittest.main()
