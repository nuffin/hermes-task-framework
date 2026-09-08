import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "compact-directory-memory"
    / "scripts"
    / "manage_directory_context.py"
)


class DirectoryContextTests(unittest.TestCase):
    def run_script(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            check=check,
        )

    def test_init_creates_frontmatter_index_and_complete_subsystem_pairs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            entity = Path(temp_dir)
            result = self.run_script("init", temp_dir, "api", "web-client")
            self.assertIn("subsystems=2", result.stdout)
            self.assertTrue((entity / "MEMORY.md").is_file())
            self.assertTrue((entity / "CHANGELOG.md").is_file())
            root_content = (entity / "MEMORY.md").read_text(encoding="utf-8")
            self.assertTrue(root_content.startswith("---\ncontext_memory:\n  children:\n"))
            for subsystem in ("api", "web-client"):
                self.assertIn(f"    - id: {subsystem}\n", root_content)
                self.assertIn(f"      memory: memories/{subsystem}/MEMORY.md\n", root_content)
                self.assertIn(f"      changelog: memories/{subsystem}/CHANGELOG.md\n", root_content)
                self.assertTrue((entity / "memories" / subsystem / "MEMORY.md").is_file())
                self.assertTrue((entity / "memories" / subsystem / "CHANGELOG.md").is_file())

    def test_init_preserves_existing_root_body_when_adding_subsystem(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            entity = Path(temp_dir)
            root_memory = entity / "MEMORY.md"
            original_body = "preserve this stable fact\n\n§\n\nAnd this one.\n"
            root_memory.write_text(original_body, encoding="utf-8")
            self.run_script("init", temp_dir, "api")
            self.run_script("init", temp_dir, "web-client")
            root_content = root_memory.read_text(encoding="utf-8")
            self.assertTrue(root_content.endswith(original_body))
            self.assertIn("    - id: api\n", root_content)
            self.assertIn("    - id: web-client\n", root_content)
            self.assertEqual(root_content.count("    - id: "), 2)

    def test_verify_rejects_incomplete_subsystem_pair(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            entity = Path(temp_dir)
            self.run_script("init", temp_dir, "api")
            (entity / "memories" / "api" / "CHANGELOG.md").unlink()
            result = self.run_script("verify", temp_dir, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn("missing subsystem file", result.stderr)

    def test_verify_rejects_missing_and_dangling_root_index_entries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            entity = Path(temp_dir)
            self.run_script("init", temp_dir, "api", "web-client")
            root_memory = entity / "MEMORY.md"
            content = root_memory.read_text(encoding="utf-8")
            root_memory.write_text(
                content.replace(
                    "    - id: web-client\n      memory: memories/web-client/MEMORY.md\n      changelog: memories/web-client/CHANGELOG.md\n",
                    "    - id: missing-child\n      memory: memories/missing-child/MEMORY.md\n      changelog: memories/missing-child/CHANGELOG.md\n",
                ),
                encoding="utf-8",
            )
            result = self.run_script("verify", temp_dir, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn("subsystem missing from root index: web-client", result.stderr)
            self.assertIn("root index references missing subsystem: missing-child", result.stderr)

    def test_verify_accepts_flat_context_without_frontmatter(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            entity = Path(temp_dir)
            (entity / "MEMORY.md").write_text("flat stable fact\n", encoding="utf-8")
            (entity / "CHANGELOG.md").write_text("# CHANGELOG.md\n", encoding="utf-8")
            result = self.run_script("verify", temp_dir)
            self.assertIn("verified flat directory context", result.stdout)

    def test_init_rejects_non_kebab_case_subsystem(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_script("init", temp_dir, "Bad_Name", check=False)
            self.assertEqual(result.returncode, 2)
            self.assertIn("lowercase kebab-case", result.stderr)


if __name__ == "__main__":
    unittest.main()
