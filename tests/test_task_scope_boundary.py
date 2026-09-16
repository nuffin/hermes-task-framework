import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANAGE = ROOT / "skills" / "task-framework" / "scripts" / "manage_task.py"
TEMPLATE = ROOT / "skills" / "task-framework" / "templates" / "TASK.md"
CORE_SKILL = ROOT / "skills" / "task-framework" / "SKILL.md"
EXTERNAL_AUDIT = ROOT / "skills" / "task-framework" / "references" / "task-types" / "external-audit.md"
ANALYSIS = ROOT / "skills" / "task-framework" / "references" / "task-types" / "analysis.md"


class TaskScopeBoundaryTests(unittest.TestCase):
    def create_task(self, root: Path) -> Path:
        environment = os.environ.copy()
        environment["HERMES_TASKS_ROOT"] = str(root)
        subprocess.run(
            [sys.executable, str(MANAGE), "create", "scope-boundary"],
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        return next(root.glob("*.scope-boundary-*"))

    def test_create_and_hard_reset_preserve_task_cache(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "tasks"
            task = self.create_task(root)
            cache_file = task / "cache" / "programming-receipt.json"
            cache_file.write_text('{"exact_match": true}\n', encoding="utf-8")

            environment = os.environ.copy()
            environment["HERMES_TASKS_ROOT"] = str(root)
            subprocess.run(
                [sys.executable, str(MANAGE), "reset", str(task)],
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertTrue((task / "input").is_dir())
            self.assertTrue((task / "output" / "docs").is_dir())
            self.assertTrue((task / "output" / "logs").is_dir())
            self.assertEqual(cache_file.read_text(encoding="utf-8"), '{"exact_match": true}\n')

    def test_template_requires_default_boundary_and_explicit_external_targets(self):
        template = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("## Scope Boundary", template)
        self.assertIn("## Authorized External Targets", template)
        self.assertIn("default and only filesystem boundary", template)
        self.assertIn("conversation explicitly names an external target", template)
        self.assertIn("absolute path or concrete external object", template)
        self.assertNotIn("<absolute path or named device/service>", template)

    def test_task_types_prohibit_implicit_repo_scope_and_require_exact_targets(self):
        framework = CORE_SKILL.read_text(encoding="utf-8")
        external_audit = EXTERNAL_AUDIT.read_text(encoding="utf-8")
        analysis = ANALYSIS.read_text(encoding="utf-8")
        self.assertIn("default filesystem boundary", framework)
        self.assertIn("Authorized External Targets", framework)
        self.assertIn("Authorized External Targets", external_audit)
        self.assertIn("当前用户明确指名", external_audit)
        self.assertIn("精确绝对路径", external_audit)
        self.assertIn("cache/", external_audit)
        self.assertNotIn("## Repo", external_audit)
        self.assertNotIn("~/project/docs/*.md", external_audit)
        self.assertNotIn("## Repo", analysis)
        self.assertIn("Authorized External Targets", analysis)
        self.assertIn("cache/", analysis)


if __name__ == "__main__":
    unittest.main()
