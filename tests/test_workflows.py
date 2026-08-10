from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import _bootstrap


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class WorkflowTests(unittest.TestCase):
    def test_repository_validator(self):
        script = _bootstrap.ROOT / ".agent-orchestrator/scripts/validate_repo.py"
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=_bootstrap.ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Repository validation passed.", result.stdout)

    def test_issue_contract_extractor_requires_one_fence(self):
        parser = load_module("parse_task_script", _bootstrap.ROOT / ".agent-orchestrator/scripts/parse_task.py")
        contract = {
            "schema": "agent-task/v1",
            "task_id": "task-01",
            "run_id": "run-01",
            "objective": "Implement a bounded and verified repository change.",
            "depends_on": [],
            "worker": {},
            "allowed_paths": ["src/**"],
            "forbidden_paths": [],
            "definition_of_done": ["Tests pass"],
            "acceptance_commands": ["python -m unittest"],
            "budget": {},
            "state": "ready",
        }
        body = "```json\n%s\n```" % json.dumps(contract)
        self.assertEqual(parser.extract_contract(body), contract)
        with self.assertRaises(ValueError):
            parser.extract_contract("no contract")
        with self.assertRaises(ValueError):
            parser.extract_contract(body + "\n" + body)

    def test_fake_worker_cli_and_status_renderer(self):
        contract = {
            "schema": "agent-task/v1",
            "task_id": "task-01",
            "run_id": "run-01",
            "objective": "Execute one bounded dry-run work unit for verification.",
            "depends_on": [],
            "worker": {"provider": "fake", "model_class": "fast", "role": "implementer"},
            "allowed_paths": ["src/**"],
            "forbidden_paths": [".git/**"],
            "definition_of_done": ["Dry-run result exists"],
            "acceptance_commands": ["python -m unittest"],
            "budget": {"max_wall_minutes": 10, "max_cost_usd": 0, "max_tokens": 1000},
            "state": "ready",
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            task_path = root / "task.json"
            result_path = root / "result.json"
            task_path.write_text(json.dumps(contract), encoding="utf-8")
            worker = subprocess.run(
                [
                    sys.executable,
                    str(_bootstrap.ROOT / ".agent-orchestrator/scripts/run_worker.py"),
                    "--task", str(task_path),
                    "--adapter", "fake",
                    "--claim-dir", str(root / "claims"),
                    "--out", str(result_path),
                ],
                cwd=_bootstrap.ROOT,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(worker.returncode, 0, worker.stdout + worker.stderr)
            self.assertTrue(json.loads(result_path.read_text(encoding="utf-8"))["result"]["dry_run"])
            claim = json.loads((root / "claims/task-01.json").read_text(encoding="utf-8"))
            self.assertEqual(claim["state"], "verifying")

            status_path = root / "status.json"
            comment_path = root / "comment.md"
            status_path.write_text(json.dumps({
                "task_id": "task-01",
                "state": "accepted",
                "summary": r"Verified at C:\private\workspace",
            }), encoding="utf-8")
            status = subprocess.run(
                [
                    sys.executable,
                    str(_bootstrap.ROOT / ".agent-orchestrator/scripts/publish_status.py"),
                    "--status", str(status_path),
                    "--out", str(comment_path),
                ],
                cwd=_bootstrap.ROOT,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
            comment = comment_path.read_text(encoding="utf-8")
            self.assertIn("[LOCAL_PATH]", comment)
            self.assertNotIn(r"C:\private", comment)


if __name__ == "__main__":
    unittest.main()
