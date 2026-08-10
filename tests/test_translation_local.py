from __future__ import annotations

import io
import json
import struct
import unittest

import _bootstrap  # noqa: F401
from bridge.native_host import handle, read_message, write_message
from orchestrator.errors import TranslationError
from orchestrator.local_backend import select_local_backend
from orchestrator.schema import validate_envelope
from translator import v11_to_v2, v2_to_v11


TASK_ID = "00000000-0000-4000-8000-000000000001"


def local_packet() -> dict:
    return {
        "protocol": "rwrouter/1.1",
        "task_id": TASK_ID,
        "execution_surface": "LOCAL",
        "objective": "Perform a bounded local acceptance check.",
        "workspace_alias": "demo",
        "task_kind": "coding",
        "acceptance_checks": ["Tests pass"],
    }


class TranslationAndLocalEdgeTests(unittest.TestCase):
    def test_local_translation_is_valid_and_path_free(self):
        envelope = v11_to_v2(local_packet())
        self.assertEqual(envelope["surface"], "LOCAL_EDGE")
        self.assertEqual(validate_envelope(envelope), [])
        self.assertNotIn(":\\", json.dumps(envelope))

    def test_cloud_surface_has_no_legacy_wire_mapping(self):
        envelope = {
            "protocol": "rwrouter/2",
            "task_id": TASK_ID,
            "surface": "GITHUB_CLOUD",
            "objective": "Implement a cloud repository task.",
        }
        with self.assertRaises(TranslationError):
            v2_to_v11(envelope)

    def test_backend_gates_runner(self):
        task = {"repository": True, "implementation": True, "task_kind": "coding"}
        self.assertEqual(select_local_backend(task, True, True)[0], "CODING_RUNNER")
        self.assertEqual(select_local_backend(task, False, True)[0], "CODEX_DIRECT")
        task["local_backend_preference"] = "CODING_RUNNER"
        self.assertEqual(select_local_backend(task, False, True)[0], "NEEDS_USER")
        self.assertEqual(select_local_backend({"planning_only": True}, True, True)[0], "CODEX_DIRECT")

    def test_native_messaging_framing_and_project_binding(self):
        stream = io.BytesIO()
        write_message(stream, {"hello": "世界"})
        stream.seek(0)
        self.assertEqual(read_message(stream), {"hello": "世界"})
        with self.assertRaises(ValueError):
            read_message(io.BytesIO(struct.pack("<I", 4) + b"{}"))

        config = {
            "bound_project_fingerprint": "project-01",
            "workspace_aliases": {"demo": "local-only"},
            "repository_aliases": {"demo": "repo"},
        }
        request = {
            "project_fingerprint": "project-01",
            "packet": local_packet(),
            "implementation": True,
            "repo_clean": True,
        }
        self.assertEqual(handle(request, config)["local_backend_selected"], "CODING_RUNNER")
        request["project_fingerprint"] = "wrong"
        with self.assertRaises(ValueError):
            handle(request, config)


if __name__ == "__main__":
    unittest.main()
