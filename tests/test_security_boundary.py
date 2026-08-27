from __future__ import annotations

import unittest

import _bootstrap  # noqa: F401
from orchestrator.boundary import check_changed_paths, enforce_changed_paths
from orchestrator.errors import BoundaryViolationError, SecurityError
from orchestrator.security import ensure_cloud_safe, redact


class SecurityAndBoundaryTests(unittest.TestCase):
    def test_cloud_payload_rejects_paths_and_credentials(self):
        with self.assertRaises(SecurityError):
            ensure_cloud_safe({"objective": r"Read C:\private\notes.txt"})
        with self.assertRaises(SecurityError):
            ensure_cloud_safe({"api_key": "should-never-leave"})
        cleaned = redact({"text": r"Read C:\private\notes.txt", "token": "secret"})
        self.assertNotIn("C:\\private", cleaned["text"])
        self.assertEqual(cleaned["token"], "[REDACTED]")
        ensure_cloud_safe({"budget": {"max_tokens": 1000}})
        with self.assertRaises(SecurityError):
            ensure_cloud_safe({"github_token": "should-never-leave"})
        with self.assertRaises(SecurityError):
            ensure_cloud_safe({"apiKey": "should-never-leave"})
        with self.assertRaises(SecurityError):
            synthetic_token = "github_" + "pat_" + "012345678901234567890123456789"
            ensure_cloud_safe({"text": synthetic_token})

    def test_changed_path_boundary(self):
        outside, blocked = check_changed_paths(
            ["src/good.py", "docs/out.md", ".git/config"],
            ["src/**"],
            [".git/**"],
        )
        self.assertEqual(outside, ["docs/out.md"])
        self.assertEqual(blocked, [".git/config"])
        with self.assertRaises(BoundaryViolationError):
            enforce_changed_paths(["../escape"], ["src/**"], [])


if __name__ == "__main__":
    unittest.main()
