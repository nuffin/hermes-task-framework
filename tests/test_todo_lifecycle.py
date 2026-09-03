import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "skills/task-framework/scripts/todo_lifecycle.py"
spec = importlib.util.spec_from_file_location("todo_lifecycle", MODULE)
todo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(todo)


class TodoLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.task = Path(self.temp.name)
        (self.task / "TASK.md").write_text(
            "# Task: example\n\n## TODO\n\n"
            "| ID | Requirement | Source | Timestamp | Status | Scope decision | Routed task / checklist |\n"
            "|---|---|---|---|---|---|---|\n\n"
            "## Checklist\n\n- [ ] Phase 1 — existing work\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_intake_records_required_fields_and_open_state(self):
        item = todo.add_todo(self.task, "Support a newly discovered case", "phase 1 post-flight")
        self.assertEqual(item["status"], "open")
        self.assertEqual(item["scope"], "open")
        parsed = todo.parse_todos((self.task / "TASK.md").read_text())
        self.assertEqual(parsed[0]["id"], "todo-1")
        self.assertEqual(parsed[0]["source"], "phase 1 post-flight")
        self.assertTrue(parsed[0]["timestamp"])
        self.assertEqual(todo.validate_todos((self.task / "TASK.md").read_text()), [])

    def test_continuous_route_decomposes_into_checklist(self):
        todo.add_todo(self.task, "Refine current phase", "phase transition")
        item = todo.update_todo(self.task, "todo-1", "continuous", "Phase 1b — refine validation")
        self.assertEqual(item["status"], "decomposed")
        text = (self.task / "TASK.md").read_text()
        self.assertIn("TODO todo-1 — Phase 1b — refine validation", text)
        self.assertEqual(todo.validate_todos(text), [])

    def test_nested_and_top_level_route_are_explicit(self):
        for scope, outcome in (("nested", "subtasks/child-123456"), ("top-level", "20260903-new-task-123456")):
            todo.add_todo(self.task, f"{scope} requirement", "post-flight")
            item = todo.update_todo(self.task, item_id := f"todo-{1 if scope == 'nested' else 2}", scope, outcome)
            self.assertEqual(item["status"], "routed")
            self.assertEqual(item["route"], outcome)
        self.assertEqual(todo.validate_todos((self.task / "TASK.md").read_text()), [])

    def test_cancelled_and_blocked_require_explicit_outcome(self):
        todo.add_todo(self.task, "Won't be pursued", "review")
        with self.assertRaises(ValueError):
            todo.set_terminal(self.task, "todo-1", "cancelled", "")
        item = todo.set_terminal(self.task, "todo-1", "cancelled", "Duplicate of existing requirement")
        self.assertEqual(item["scope"], "cancelled")
        self.assertEqual(todo.validate_todos((self.task / "TASK.md").read_text()), [])

    def test_open_todo_is_not_silently_finalized(self):
        todo.add_todo(self.task, "Still needs classification", "phase 2")
        text = (self.task / "TASK.md").read_text()
        self.assertEqual(todo.parse_todos(text)[0]["status"], "open")
        self.assertNotIn("completed", text)

    def test_pipe_values_round_trip_and_finalized_rows_cannot_change(self):
        todo.add_todo(self.task, "Requirement | with a pipe", "review | post-flight")
        parsed = todo.parse_todos((self.task / "TASK.md").read_text())
        self.assertEqual(parsed[0]["requirement"], "Requirement | with a pipe")
        todo.set_terminal(self.task, "todo-1", "blocked", "Waiting for API decision")
        with self.assertRaises(ValueError):
            todo.update_todo(self.task, "todo-1", "continuous", "Phase 2")

    def test_malformed_rows_are_reported(self):
        text = (self.task / "TASK.md").read_text()
        text = text.replace("|---|---|---|---|---|---|---|", "|---|---|---|---|---|---|---|\n| todo-1 | incomplete | source | timestamp | open |")
        self.assertTrue(todo.validate_todos(text))


if __name__ == "__main__":
    unittest.main()
