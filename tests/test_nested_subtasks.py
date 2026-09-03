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
        self.assertRegex(child.name, r"^\d{8}-\d{6}\.child-[a-z0-9]{6}$")
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

    def test_legacy_child_name_is_migrated_and_resolved_without_touching_input(self):
        child = self.parent / "subtasks" / "oidc-client-error-diagnostics-5283c1"
        child.mkdir(parents=True)
        (child / "TASK.md").write_text(
            "# Task: oidc-client-error-diagnostics\n\n"
            "## Status\n\ncompleted\n\n## Goal\n\nLegacy child\n"
        )
        (child / "input").mkdir()
        source = child / "input" / "fixture.txt"
        source.write_text("must remain unchanged")
        (child / ".hermes-task.json").write_text(json.dumps({
            "hash": "5283c1", "name": "oidc-client-error-diagnostics",
        }))

        by_hash = json.loads(self.run_api("describe", "5283c1").stdout)
        by_name = json.loads(self.run_api("describe", "oidc-client-error-diagnostics").stdout)
        by_path = json.loads(self.run_api("describe", str(child)).stdout)
        for described in (by_hash, by_name, by_path):
            self.assertEqual(described["path"], str(child.resolve()))
            self.assertIsNone(described["parent"])
        self.assertIn(child.name, self.run_manage("view", self.phash).stdout)
        self.assertIn(child.name, self.run_manage("list", self.phash).stdout)

        before = source.read_bytes()
        parent_task = (self.parent / "TASK.md").read_text()
        (self.parent / "TASK.md").write_text(
            parent_task + f"\nLegacy child: subtasks/{child.name}\n")
        (self.parent / "README.md").write_text(f"legacy={child.name}\n")
        (child / "MEMORY.md").write_text(f"legacy={child.name}\n")
        (child / "CHANGELOG.md").write_text(f"legacy={child.name}\n")
        self.run_manage("reindex")
        renamed = next((self.parent / "subtasks").glob("202*.*-5283c1"))
        self.assertNotEqual(renamed.name, child.name)
        self.assertFalse(child.exists())
        metadata = json.loads((renamed / ".hermes-task.json").read_text())
        self.assertEqual(metadata["parent_hash"], self.phash)
        self.assertEqual(metadata["parent_path"], self.parent.name)
        self.assertTrue(metadata["is_subtask"])
        self.assertEqual((renamed / "input" / "fixture.txt").read_bytes(), before)
        self.assertIn(renamed.name, (self.root / "TASKS.md").read_text())
        self.assertNotIn(renamed.name, self.run_manage("list").stdout)
        self.assertIn(f"subtasks/{renamed.name}", (self.parent / "TASK.md").read_text())
        for artifact in (self.parent / "README.md", renamed / "MEMORY.md", renamed / "CHANGELOG.md"):
            content = artifact.read_text()
            self.assertIn(renamed.name, content)
            self.assertNotIn(f"subtasks/{child.name}", content)

    def test_symlinked_legacy_child_is_not_discovered(self):
        outside = Path(tempfile.mkdtemp())
        try:
            (outside / "TASK.md").write_text("# Task: outside")
            link = self.parent / "subtasks" / "legacy-link-aaaaaa"
            try:
                link.symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"symlinks unavailable: {exc}")
            self.assertNotIn("legacy-link-aaaaaa", self.run_manage("list", self.phash).stdout)
            result = self.run_api("describe", str(link), check=False)
            self.assertNotEqual(result.returncode, 0)
        finally:
            import shutil
            shutil.rmtree(outside)

if __name__ == "__main__":
    unittest.main()
