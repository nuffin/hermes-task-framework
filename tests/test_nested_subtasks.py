import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANAGE = ROOT / "skills/task-framework/scripts/manage_task.py"
API = ROOT / "skills/task-framework/scripts/task_api.py"

class NestedSubtaskTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = os.environ | {"HERMES_TASKS_ROOT": str(self.root)}
        self.env.pop("HERMES_TASKS_DIR", None)
        subprocess.run([sys.executable, str(MANAGE), "create", "parent", "--desc", "Parent"], env=self.env, check=True, capture_output=True, text=True)
        self.parent = next(self.root.glob("*.parent-*"))
        self.phash = json.loads((self.parent / ".hermes-task.json").read_text())["hash"]

    def tearDown(self):
        self.temp.cleanup()

    def run_manage(self, *args, check=True):
        return subprocess.run([sys.executable, str(MANAGE), *args], env=self.env, check=check, capture_output=True, text=True)

    def run_api(self, *args, check=True):
        return subprocess.run([sys.executable, str(API), *args], env=self.env, check=check, capture_output=True, text=True)

    def test_create_describe_and_root_index_containment(self):
        result = self.run_manage("create", "child", "--parent", self.phash, "--desc", "Child")
        child = next((self.parent / "subtasks").glob("*.child-*"))
        meta = json.loads((child / ".hermes-task.json").read_text())
        self.assertEqual(meta["parent_hash"], self.phash)
        self.assertEqual(meta["parent_path"], self.parent.name)
        self.assertTrue(meta["is_subtask"])
        chash = meta["hash"]
        described = json.loads(self.run_api("describe", chash).stdout)
        self.assertEqual(described["parent"]["hash"], self.phash)
        parent_view = json.loads(self.run_api("describe", self.phash).stdout)
        self.assertEqual(parent_view["children"][0]["hash"], chash)
        root_list = self.run_manage("list").stdout
        self.assertIn("parent-", root_list)
        self.assertNotIn(child.name, root_list)
        index = (self.root / "TASKS.md").read_text()
        self.assertIn("Subtasks", index)
        self.assertIn(child.name, index)
        self.assertEqual(result.returncode, 0)

    def test_invalid_or_nested_parent_rejected_without_writes(self):
        bad = self.run_manage("create", "orphan", "--parent", "ffffff", check=False)
        self.assertNotEqual(bad.returncode, 0)
        self.assertFalse(list(self.root.glob("*.orphan-*")))
        self.run_manage("create", "child", "--parent", self.phash)
        child = next((self.parent / "subtasks").glob("*.child-*"))
        chash = json.loads((child / ".hermes-task.json").read_text())["hash"]
        nested = self.run_manage("create", "grandchild", "--parent", chash, check=False)
        self.assertNotEqual(nested.returncode, 0)
        self.assertFalse(list(child.glob("subtasks/*.grandchild-*")))

    def test_status_and_reset_preserve_input(self):
        self.run_manage("create", "child", "--parent", self.phash)
        child = next((self.parent / "subtasks").glob("*.child-*"))
        chash = json.loads((child / ".hermes-task.json").read_text())["hash"]
        (child / "input/source.txt").write_text("keep")
        (child / "output/logs/generated.txt").write_text("remove")
        self.run_manage("status", chash, "done")
        self.assertIn("done", (child / "TASK.md").read_text())
        self.run_manage("reset", chash)
        self.assertEqual((child / "input/source.txt").read_text(), "keep")
        self.assertFalse((child / "output/logs/generated.txt").exists())

    def test_parent_view_and_scoped_list_discover_children(self):
        self.run_manage("create", "child", "--parent", self.phash)
        child = next((self.parent / "subtasks").glob("*.child-*"))
        self.assertIn(child.name, self.run_manage("view", self.phash).stdout)
        self.assertIn(child.name, self.run_manage("list", self.phash).stdout)

if __name__ == "__main__":
    unittest.main()
