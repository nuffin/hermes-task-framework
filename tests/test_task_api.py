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
