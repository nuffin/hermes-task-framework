import tempfile
import unittest
import subprocess
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "task-framework" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from task_symlink_policy import inspect_task, inspect_tasks_root  # noqa: E402


class TaskSymlinkPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.tasks_root = Path(self.temporary.name) / "tasks"
        self.task = self.tasks_root / "20260905-120000.symlink-policy-a1b2c3"
        (self.task / "input").mkdir(parents=True)
        for name in ("TASK.md", "README.md", "MEMORY.md", "CHANGELOG.md", ".hermes-task.json"):
            (self.task / name).write_text(name + "\n", encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def test_allows_existing_relative_target_inside_task(self):
        (self.task / "input" / "payload").mkdir()
        (self.task / "input" / "alias").symlink_to("payload")
        report = inspect_task(self.task)
        self.assertTrue(report["ok"])
        self.assertEqual(report["symlinks"][0]["reason"], "relative contained target")

    def test_rejects_absolute_target(self):
        outside = Path(self.temporary.name) / "outside"
        outside.write_text("outside\n", encoding="utf-8")
        (self.task / "input" / "absolute").symlink_to(outside)
        report = inspect_task(self.task)
        self.assertFalse(report["ok"])
        self.assertEqual(report["rejected"][0]["reason"], "absolute target")

    def test_rejects_missing_and_escaping_relative_targets(self):
        (self.task / "input" / "missing").symlink_to("not-present")
        outside = self.tasks_root / "outside"
        outside.write_text("outside\n", encoding="utf-8")
        (self.task / "input" / "escape").symlink_to("../../outside")
        report = inspect_task(self.task)
        self.assertFalse(report["ok"])
        self.assertEqual({entry["reason"] for entry in report["rejected"]}, {"missing target", "target escapes task root"})

    def test_rejects_canonical_task_symlink(self):
        (self.task / ".hermes-task.json").unlink()
        (self.task / "input" / "metadata").write_text("{}\n", encoding="utf-8")
        (self.task / ".hermes-task.json").symlink_to("input/metadata")
        report = inspect_task(self.task)
        self.assertFalse(report["ok"])
        self.assertEqual(report["rejected"][0]["reason"], "canonical task file must be regular")

    def test_ignores_non_task_git_recovery_tree(self):
        outside = Path(self.temporary.name) / "outside"
        outside.write_text("outside\n", encoding="utf-8")
        recovery = self.tasks_root / ".git" / "task-sync" / "checkpoint" / "integration"
        recovery.mkdir(parents=True)
        (recovery / "unsafe").symlink_to(outside)
        report = inspect_tasks_root(self.tasks_root)
        self.assertTrue(report["ok"])
        self.assertEqual(report["symlinks"], [])

    def test_ignores_git_ignored_runtime_symlinks(self):
        subprocess.run(["git", "init", "--initial-branch=main", str(self.tasks_root)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.tasks_root), "config", "user.name", "Test"], check=True)
        subprocess.run(["git", "-C", str(self.tasks_root), "config", "user.email", "test@example.invalid"], check=True)
        (self.tasks_root / ".gitignore").write_text("**/.venv/\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.tasks_root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.tasks_root), "commit", "-m", "fixture"], check=True, capture_output=True)
        environment = self.task / "repos" / "service" / ".venv" / "bin"
        environment.mkdir(parents=True)
        (environment / "python").symlink_to("/usr/bin/python3")
        report = inspect_tasks_root(self.tasks_root)
        self.assertTrue(report["ok"])
        self.assertEqual(report["symlinks"], [])

    def test_rejects_tasks_root_index_symlink(self):
        outside = Path(self.temporary.name) / "outside-index"
        outside.write_text("outside\n", encoding="utf-8")
        (self.tasks_root / "README.md").symlink_to(outside)
        report = inspect_tasks_root(self.tasks_root)
        self.assertFalse(report["ok"])
        self.assertEqual(report["rejected"][0]["reason"], "root index must be regular")


if __name__ == "__main__":
    unittest.main()
