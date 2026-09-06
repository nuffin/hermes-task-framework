import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANAGE = ROOT / "skills" / "task-framework" / "scripts" / "manage_task.py"
INTEGRITY = ROOT / "skills" / "task-artifact-integrity" / "scripts" / "task_integrity.py"


class TaskIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.tasks_root = Path(self.temp.name) / "tasks"
        self.tasks_root.mkdir()
        self.env = os.environ.copy()
        self.env["HERMES_TASKS_ROOT"] = str(self.tasks_root)
        subprocess.run(
            [sys.executable, str(MANAGE), "create", "integrity-test", "--desc", "Integrity fixture"],
            env=self.env,
            check=True,
            capture_output=True,
            text=True,
        )
        self.task_dir = next(self.tasks_root.glob("*.integrity-test-*"))
        self.task_hash = json.loads((self.task_dir / ".hermes-task.json").read_text())["hash"]

    def tearDown(self):
        self.temp.cleanup()

    def run_integrity(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(INTEGRITY), *args],
            env=self.env,
            check=check,
            capture_output=True,
            text=True,
        )

    def test_audit_accepts_complete_task(self):
        result = json.loads(self.run_integrity("audit", self.task_hash).stdout)
        self.assertTrue(result["ok"])
        self.assertEqual(result["errors"], [])

    def test_audit_rejects_missing_canonical_file(self):
        (self.task_dir / "MEMORY.md").unlink()
        process = self.run_integrity("audit", self.task_hash, check=False)
        self.assertEqual(process.returncode, 1)
        result = json.loads(process.stdout)
        self.assertIn("missing canonical file: MEMORY.md", result["errors"])

    def test_manifest_compare_detects_changes(self):
        destination = Path(self.temp.name) / "destination"
        shutil.copytree(self.task_dir, destination)
        equal = json.loads(self.run_integrity("compare", str(self.task_dir), str(destination)).stdout)
        self.assertTrue(equal["equal"])
        (destination / "README.md").write_text("changed\n", encoding="utf-8")
        process = self.run_integrity("compare", str(self.task_dir), str(destination), check=False)
        self.assertEqual(process.returncode, 1)
        changed = json.loads(process.stdout)
        self.assertIn("README.md", changed["changed"])
    def test_symlink_and_post_flight_cli_allow_relative_contained_input_alias(self):
        (self.task_dir / "input" / "payload").mkdir()
        (self.task_dir / "input" / "alias").symlink_to("payload")
        symlinks = json.loads(self.run_integrity("symlinks", self.task_hash).stdout)
        self.assertTrue(symlinks["ok"])
        self.assertEqual(symlinks["symlinks"][0]["reason"], "relative contained target")
        post_flight = json.loads(self.run_integrity("post-flight", self.task_hash).stdout)
        self.assertTrue(post_flight["ok"])
        self.assertEqual(post_flight["scope"], "task")
        self.assertEqual(post_flight["phase"], "post-flight")

    def test_symlink_cli_rejects_absolute_target(self):
        outside = Path(self.temp.name) / "outside"
        outside.write_text("outside\n", encoding="utf-8")
        (self.task_dir / "input" / "external").symlink_to(outside)
        process = self.run_integrity("symlinks", self.task_hash, check=False)
        self.assertEqual(process.returncode, 1)
        result = json.loads(process.stdout)
        self.assertEqual(result["rejected"][0]["reason"], "absolute target")


if __name__ == "__main__":
    unittest.main()
