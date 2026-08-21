import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


class SkillOwnershipTests(unittest.TestCase):
    def test_planned_task_framework_skills_exist(self):
        names = {
            "task-framework",
            "task-context-storage",
            "compact-directory-memory",
            "task-lifecycle-discipline",
            "task-timestamp-convention",
            "task-tracker",
            "task-aware-project-work",
            "task-artifact-integrity",
            "task-archaeology",
            "task-lifecycle-edge-cases",
            "task-lifecycle-portability",
            "task-external-repos-pattern",
            "task-cross-machine-sync",
        }
        for name in names:
            self.assertTrue((SKILLS / name / "SKILL.md").is_file(), name)

    def test_absorbed_skills_are_not_separate_modules(self):
        for name in ("task-initialization-sequence", "task-create-first", "pipeline-output-model"):
            self.assertFalse((SKILLS / name).exists(), name)

    def test_cross_machine_sync_is_portable(self):
        text = (SKILLS / "task-cross-machine-sync" / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("nuffin/hermes-tasks", text)
        self.assertNotIn("Machine A", text)
        self.assertIn("explicit authorization", text)

    def test_task_aware_uses_canonical_context(self):
        text = (SKILLS / "task-aware-project-work" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("task_api.py describe", text)
        self.assertIn("Legacy `TASK_MEMORY.md` is not canonical", text)

    def test_portability_has_no_legacy_mirror_commands(self):
        paths = [
            SKILLS / "task-lifecycle-portability" / "SKILL.md",
            SKILLS / "task-lifecycle-portability" / "references" / "output-model-design.md",
        ]
        forbidden = ("relink <hash>", "personal-tasks/<hash>", "restore symlinks", "converted to symlinks")
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for value in forbidden:
                self.assertNotIn(value, text, f"{path}: {value}")

    def test_task_ref_uses_canonical_fallback(self):
        text = (SKILLS / "task-framework" / "scripts" / "task_ref.py").read_text(encoding="utf-8")
        self.assertIn("~/studio/hermes/tasks", text)
        self.assertNotIn('return os.path.expanduser("~/.hermes/tasks")', text)


if __name__ == "__main__":
    unittest.main()
