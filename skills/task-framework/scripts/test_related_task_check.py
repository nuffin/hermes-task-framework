#!/usr/bin/env python3
"""Focused regression checks for create related-task preflight."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
MANAGE = SCRIPTS / "manage_task.py"
API = SCRIPTS / "task_api.py"


def write_task(root: Path, directory: str, name: str, goal: str, body: str = "") -> Path:
    task_dir = root / directory
    task_dir.mkdir()
    (task_dir / ".hermes-task.json").write_text(json.dumps({"name": name, "hash": "abc123"}), encoding="utf-8")
    (task_dir / "TASK.md").write_text(
        f"# Task: {name}\n\n## Status\n\nactive\n\n## Goal\n\n{goal}\n\n## Notes\n\n{body}\n",
        encoding="utf-8",
    )
    return task_dir


class RelatedTaskPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.existing = write_task(
            self.root,
            "20260101-000000.release-dashboard-abc123",
            "release-dashboard",
            "Automate deployment dashboard alerts.",
            "Dashboard deployment must preserve alert routing.",
        )
        self.env = {**os.environ, "HERMES_TASKS_ROOT": str(self.root)}

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(MANAGE), *args], env=self.env,
            text=True, capture_output=True, check=False,
        )

    def test_create_refuses_related_task_without_creating(self):
        result = self.run_cli("create", "dashboard-release-notification", "--desc", "Automate deployment dashboard alerts")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Related existing tasks found; no task was created:", result.stdout)
        self.assertIn("dir=20260101-000000.release-dashboard-abc123", result.stdout)
        self.assertIn("goal=Automate deployment dashboard alerts.", result.stdout)
        self.assertIn("reason=domain anchor:", result.stdout)
        self.assertIn("--allow-related", result.stdout)
        self.assertEqual(sorted(path.name for path in self.root.iterdir()), [self.existing.name])

    def test_allow_related_explicitly_creates_separate_task(self):
        result = self.run_cli(
            "create", "dashboard-release-notification", "--desc", "Automate deployment dashboard alerts", "--allow-related"
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Created task:", result.stdout)
        self.assertEqual(len([path for path in self.root.iterdir() if (path / "TASK.md").is_file()]), 2)

    def test_allow_duplicate_remains_compatible(self):
        result = self.run_cli("create", "release-dashboard", "--allow-duplicate")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Created task:", result.stdout)
        self.assertEqual(len([path for path in self.root.iterdir() if (path / "TASK.md").is_file()]), 2)

    def test_related_api_returns_stable_candidate_fields(self):
        result = subprocess.run(
            [sys.executable, str(API), "related", "dashboard-release-notification", "--desc", "Automate deployment dashboard alerts"],
            env=self.env, text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        candidates = json.loads(result.stdout)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["directory"], self.existing.name)
        self.assertEqual(candidates[0]["title"], "release-dashboard")
        self.assertEqual(candidates[0]["goal"], "Automate deployment dashboard alerts.")
        self.assertIn("Goal", candidates[0]["reason"])
        self.assertNotIn("TASK.md", candidates[0]["reason"])

    def test_generic_terms_and_task_body_backlink_do_not_create_candidates(self):
        noise = write_task(
            self.root,
            "20260102-000000.rust-rewrite-architecture-def456",
            "rust-rewrite-architecture",
            "Improve baseline performance for the legacy service.",
            "Parent task backlink: polis agora token factory.",
        )
        result = subprocess.run(
            [sys.executable, str(API), "related", "polis agora rust rewrite",
             "--desc", "Rust rewrite baseline performance architecture"],
            env=self.env, text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [])
        self.assertTrue(noise.is_dir())

    def test_domain_anchor_and_phrase_find_agora_polis_and_token_factory(self):
        agora = write_task(
            self.root,
            "20260103-000000.agora-governance-aaa111",
            "agora-governance",
            "Implement the Agora governance workflow.",
        )
        polis = write_task(
            self.root,
            "20260104-000000.polis-consensus-bbb222",
            "polis-consensus",
            "Document Polis consensus integration.",
        )
        token_factory = write_task(
            self.root,
            "20260105-000000.token-factory-ccc333",
            "token-factory",
            "Ship the Token Factory deployment contract.",
        )
        for query, expected in (("agora delegation", agora.name),
                                ("polis reporting", polis.name),
                                ("token factory audit", token_factory.name)):
            result = subprocess.run(
                [sys.executable, str(API), "related", query], env=self.env,
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            candidates = json.loads(result.stdout)
            self.assertIn(expected, [candidate["directory"] for candidate in candidates])
        token_result = subprocess.run(
            [sys.executable, str(API), "related", "token factory audit"], env=self.env,
            text=True, capture_output=True, check=False,
        )
        token_candidate = next(candidate for candidate in json.loads(token_result.stdout)
                               if candidate["directory"] == token_factory.name)
        self.assertIn("shared phrase: token factory", token_candidate["reason"])

    def test_search_includes_task_md_body(self):
        result = subprocess.run(
            [sys.executable, str(API), "search", "preserve alert routing"],
            env=self.env, text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        results = json.loads(result.stdout)
        self.assertEqual([item["directory"] for item in results], [self.existing.name])


if __name__ == "__main__":
    unittest.main()
