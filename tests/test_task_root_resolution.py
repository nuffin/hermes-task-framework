import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "task-framework"
    / "scripts"
    / "manage_task.py"
)


def load_manage_task():
    spec = importlib.util.spec_from_file_location("manage_task_under_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TaskRootResolutionTests(unittest.TestCase):
    def setUp(self):
        self.original = {
            "HERMES_TASKS_ROOT": os.environ.get("HERMES_TASKS_ROOT"),
            "HERMES_TASKS_DIR": os.environ.get("HERMES_TASKS_DIR"),
            "HERMES_HOME": os.environ.get("HERMES_HOME"),
        }
        os.environ["HERMES_HOME"] = "/tmp/hermes-task-framework-test-profile"

    def tearDown(self):
        for key, value in self.original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_root_is_canonical_when_both_variables_are_set(self):
        os.environ["HERMES_TASKS_ROOT"] = "/tmp/canonical-tasks"
        os.environ["HERMES_TASKS_DIR"] = "/tmp/legacy-tasks"
        module = load_manage_task()
        self.assertEqual(module.TASKS_ROOT, "/tmp/canonical-tasks")

    def test_legacy_dir_is_used_as_fallback(self):
        os.environ.pop("HERMES_TASKS_ROOT", None)
        os.environ["HERMES_TASKS_DIR"] = "/tmp/legacy-tasks"
        module = load_manage_task()
        self.assertEqual(module.TASKS_ROOT, "/tmp/legacy-tasks")

    def test_create_command_uses_root_without_legacy_alias(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env = os.environ.copy()
            env["HERMES_TASKS_ROOT"] = temp_dir
            env.pop("HERMES_TASKS_DIR", None)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "create", "root-only-test"],
                cwd=SCRIPT.parent,
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn(temp_dir, result.stdout)
            created = list(Path(temp_dir).glob("*.root-only-test-*"))
            self.assertEqual(len(created), 1)
            self.assertTrue((created[0] / ".hermes-task.json").exists())


if __name__ == "__main__":
    unittest.main()
