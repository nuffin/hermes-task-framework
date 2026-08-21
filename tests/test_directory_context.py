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

    def test_init_creates_complete_subsystem_pairs_without_overwriting(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            entity = Path(temp_dir)
            result = self.run_script("init", temp_dir, "api", "web-client")
            self.assertIn("subsystems=2", result.stdout)
            self.assertTrue((entity / "MEMORY.md").is_file())
            self.assertTrue((entity / "CHANGELOG.md").is_file())
            for subsystem in ("api", "web-client"):
                self.assertTrue((entity / "memories" / subsystem / "MEMORY.md").is_file())
                self.assertTrue((entity / "memories" / subsystem / "CHANGELOG.md").is_file())
            root_memory = entity / "MEMORY.md"
            root_memory.write_text("preserve me\n", encoding="utf-8")
            self.run_script("init", temp_dir, "api")
            self.assertEqual(root_memory.read_text(encoding="utf-8"), "preserve me\n")

    def test_verify_rejects_incomplete_subsystem_pair(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            entity = Path(temp_dir)
            self.run_script("init", temp_dir, "api")
            (entity / "memories" / "api" / "CHANGELOG.md").unlink()
            result = self.run_script("verify", temp_dir, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn("missing subsystem file", result.stderr)

    def test_init_rejects_non_kebab_case_subsystem(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_script("init", temp_dir, "Bad_Name", check=False)
            self.assertEqual(result.returncode, 2)
            self.assertIn("lowercase kebab-case", result.stderr)


if __name__ == "__main__":
    unittest.main()
