import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "task-cross-machine-sync" / "scripts" / "task_git_sync.py"
POLICY_SCRIPT = ROOT / "skills" / "task-cross-machine-sync" / "scripts"
sys.path.insert(0, str(POLICY_SCRIPT))
from branch_policy import (  # noqa: E402
    DEFAULT_PATH,
    discover_policy,
    promotion_steps,
    validate_promotion,
)


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

    def test_missing_policy_uses_generic_three_stage_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            policy = discover_policy(temp_dir)
            self.assertEqual(policy.path, DEFAULT_PATH)
            self.assertFalse(policy.explicit)
            validate_promotion(policy, "feat/login", "develop")
            validate_promotion(policy, "develop", "main")

    def test_json_policy_controls_next_hop_without_hardcoding_repo(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".branch-promotion.json").write_text(
                '{"promotion_path": ["feature", "integration", "production"]}\n',
                encoding="utf-8",
            )
            policy = discover_policy(root)
            self.assertEqual(policy.path, ("feature", "integration", "production"))
            validate_promotion(policy, "feature/login", "integration")
            with self.assertRaisesRegex(ValueError, "expected integration"):
                validate_promotion(policy, "feature/login", "production")

    def test_document_policy_is_used_when_config_is_absent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "CONTRIBUTING.md").write_text(
                "Changes promote `develop` -> `main`; release follows later.\n",
                encoding="utf-8",
            )
            policy = discover_policy(root)
            self.assertEqual(policy.path, ("develop", "main"))
            validate_promotion(policy, "develop", "main")

    def test_promotion_steps_are_ff_only_and_never_force(self):
        steps = promotion_steps("feat/login", "develop", "upstream")
        self.assertEqual(steps[0], ("git", "merge", "--ff-only", "feat/login"))
        self.assertEqual(steps[1], ("git", "push", "upstream", "HEAD:develop"))
        self.assertNotIn("--force", sum((list(step) for step in steps), []))


if __name__ == "__main__":
    unittest.main()
