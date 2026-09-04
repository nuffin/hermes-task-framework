import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANAGE = ROOT / "skills" / "task-framework" / "scripts" / "manage_task.py"
API = ROOT / "skills" / "task-framework" / "scripts" / "task_api.py"


class TaskApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.tasks_root = Path(self.temp.name)
        self.env = os.environ.copy()
        self.env["HERMES_TASKS_ROOT"] = str(self.tasks_root)
        self.env.pop("HERMES_TASKS_DIR", None)
        subprocess.run(
            [sys.executable, str(MANAGE), "create", "adapter-api-test", "--desc", "Stable adapter API test"],
            env=self.env,
            check=True,
            capture_output=True,
            text=True,
        )
        self.task_dir = next(self.tasks_root.glob("*.adapter-api-test-*"))
        self.task_hash = json.loads((self.task_dir / ".hermes-task.json").read_text())["hash"]

    def tearDown(self):
        self.temp.cleanup()

    def run_api(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(API), *args],
            env=self.env,
            check=check,
            capture_output=True,
            text=True,
        )

    def test_describe_resolves_hash_and_returns_canonical_fields(self):
        result = json.loads(self.run_api("describe", self.task_hash).stdout)
        self.assertEqual(result["hash"], self.task_hash)
        self.assertEqual(result["name"], "adapter-api-test")
        self.assertEqual(result["goal"], "Stable adapter API test")
        self.assertTrue(Path(result["path"]).samefile(self.task_dir))
        self.assertTrue(result["checklist"])
        self.assertEqual(result["checklist"][0]["kind"], "phase")

    def test_search_matches_name_and_goal(self):
        results = json.loads(self.run_api("search", "adapter API").stdout)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["hash"], self.task_hash)

    def test_set_and_get_extension_metadata(self):
        value = '["ticket-1", "ticket-2"]'
        self.run_api("set-extension", self.task_hash, "ticket", "related_tickets", value)
        result = json.loads(
            self.run_api("get-extension", self.task_hash, "ticket", "related_tickets").stdout
        )
        self.assertEqual(result, ["ticket-1", "ticket-2"])
        metadata = json.loads((self.task_dir / ".hermes-task.json").read_text())
        self.assertEqual(metadata["extensions"]["ticket"]["related_tickets"], result)

    def test_remote_dispatch_receipt_is_namespaced_and_idempotent(self):
        receipt = {
            "task_hash": self.task_hash,
            "controller_node": "controller",
            "executor_node": "executor",
            "dispatch_id": "dispatch-001",
            "tmux_session": "hermes-runtime",
            "tmux_window": f"task-{self.task_hash}",
            "task_dir": str(self.task_dir),
            "executor_profile": f"{self.task_hash}--remote-task-orchestrator--worker",
            "status": "dispatched",
        }
        first = json.loads(self.run_api("set-remote-dispatch", self.task_hash, json.dumps(receipt)).stdout)
        second = json.loads(self.run_api("set-remote-dispatch", self.task_hash, json.dumps(receipt)).stdout)
        self.assertFalse(first["idempotent"])
        self.assertTrue(second["idempotent"])

        stored = json.loads(self.run_api("get-extension", self.task_hash, "remote_execution", "receipt").stdout)
        self.assertEqual(stored, receipt)
        metadata = json.loads((self.task_dir / ".hermes-task.json").read_text())
        self.assertEqual(metadata["extensions"]["remote_execution"]["receipt"], receipt)

    def test_remote_dispatch_rejects_mismatched_task_and_conflicting_receipt(self):
        receipt = {
            "task_hash": "ffffff",
            "controller_node": "controller",
            "executor_node": "executor",
            "dispatch_id": "dispatch-001",
            "tmux_session": "hermes-runtime",
            "tmux_window": f"task-{self.task_hash}",
            "task_dir": str(self.task_dir),
            "executor_profile": f"{self.task_hash}--remote-task-orchestrator--worker",
            "status": "dispatched",
        }
        rejected = self.run_api("set-remote-dispatch", self.task_hash, json.dumps(receipt), check=False)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("task_hash", json.loads(rejected.stderr)["error"])

        receipt["task_hash"] = self.task_hash
        self.run_api("set-remote-dispatch", self.task_hash, json.dumps(receipt))
        receipt["dispatch_id"] = "dispatch-002"
        conflict = self.run_api("set-remote-dispatch", self.task_hash, json.dumps(receipt), check=False)
        self.assertNotEqual(conflict.returncode, 0)
        self.assertIn("already exists", json.loads(conflict.stderr)["error"])

    def test_remote_result_requires_matching_receipt_and_safe_outputs(self):
        receipt = {
            "task_hash": self.task_hash,
            "controller_node": "controller",
            "executor_node": "executor",
            "dispatch_id": "dispatch-001",
            "tmux_session": "hermes-runtime",
            "tmux_window": f"task-{self.task_hash}",
            "task_dir": str(self.task_dir),
            "executor_profile": f"{self.task_hash}--remote-task-orchestrator--worker",
            "status": "dispatched",
        }
        self.run_api("set-remote-dispatch", self.task_hash, json.dumps(receipt))
        manifest = {
            "task_hash": self.task_hash,
            "dispatch_id": "dispatch-001",
            "executor_node": "executor",
            "source_commit": "0123456789abcdef",
            "status": "pending_review",
            "outputs": [{"name": "summary", "path": "output/docs/SUMMARY.md", "bytes": 12, "sha256": "a" * 64}],
        }
        first = json.loads(self.run_api("record-remote-result", self.task_hash, json.dumps(manifest)).stdout)
        replay = json.loads(self.run_api("record-remote-result", self.task_hash, json.dumps(manifest)).stdout)
        self.assertFalse(first["idempotent"])
        self.assertTrue(replay["idempotent"])
        stored = json.loads(self.run_api("get-extension", self.task_hash, "remote_execution", "result").stdout)
        self.assertEqual(stored, manifest)

        conflict_manifest = {**manifest, "source_commit": "fedcba9876543210"}
        conflict = self.run_api("record-remote-result", self.task_hash, json.dumps(conflict_manifest), check=False)
        self.assertNotEqual(conflict.returncode, 0)
        self.assertIn("already exists", json.loads(conflict.stderr)["error"])

        manifest["outputs"][0]["path"] = "../escape.md"
        rejected = self.run_api("record-remote-result", self.task_hash, json.dumps(manifest), check=False)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("safe task-relative", json.loads(rejected.stderr)["error"])

    def test_missing_task_returns_structured_error(self):
        result = self.run_api("describe", "ffffff", check=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn("task not found", json.loads(result.stderr)["error"])

    def test_ambiguous_name_returns_candidates_instead_of_selecting_first(self):
        subprocess.run(
            [sys.executable, str(MANAGE), "create", "adapter-api-test", "--allow-duplicate"],
            env=self.env, check=True, capture_output=True, text=True,
        )
        result = self.run_api("describe", "adapter-api-test", check=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn("ambiguous task identifier", json.loads(result.stderr)["error"])


if __name__ == "__main__":
    unittest.main()
