import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "task-cross-machine-sync" / "scripts" / "task_git_sync.py"


class TaskGitSyncTests(unittest.TestCase):
    def run_script(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, check=check
        )

    def test_status_reports_clean_repository(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            subprocess.run(["git", "init", "-b", "main", str(root)], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
            (root / "README.md").write_text("fixture\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "README.md"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-m", "fixture"], check=True, capture_output=True)
            result = json.loads(self.run_script("status", "--tasks-root", str(root)).stdout)
            self.assertTrue(result["clean"])
            self.assertEqual(result["branch"], "main")

    def test_status_rejects_non_repository(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            process = self.run_script("status", "--tasks-root", temp_dir, check=False)
            self.assertEqual(process.returncode, 1)
            self.assertIn("not a Git repository", json.loads(process.stderr)["error"])

    def test_pull_requires_execute_before_network(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            subprocess.run(["git", "init", "-b", "main", str(root)], check=True, capture_output=True)
            process = self.run_script(
                "pull", "--tasks-root", str(root), "--remote", "origin", "--branch", "main", check=False
            )
            self.assertEqual(process.returncode, 1)
            self.assertIn("without --execute", json.loads(process.stderr)["error"])


if __name__ == "__main__":
    unittest.main()
