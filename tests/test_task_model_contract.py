import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANAGE = ROOT / "skills" / "task-framework" / "scripts" / "manage_task.py"


class TaskModelContractTests(unittest.TestCase):
    def create_task(self, env, *extra):
        subprocess.run(
            [sys.executable, str(MANAGE), "create", "model-contract", *extra],
            env=env, check=True, capture_output=True, text=True,
        )
        task_dir = next(Path(env["HERMES_TASKS_ROOT"]).glob("*.model-contract-*"))
        return json.loads((task_dir / ".hermes-task.json").read_text(encoding="utf-8"))

    def test_explicit_model_is_persisted_and_wins_over_launch_environment(self):
        with tempfile.TemporaryDirectory() as temporary:
            env = os.environ.copy()
            env["HERMES_TASKS_ROOT"] = temporary
            env["HERMES_INFERENCE_MODEL"] = "openai/env-model"
            metadata = self.create_task(env, "--model", "openai/explicit-model", "--provider", "openai-codex")
            execution = metadata["extensions"]["remote_execution"]
            self.assertEqual(execution, {
                "model": "openai/explicit-model", "model_source": "explicit",
                "provider": "openai-codex", "provider_source": "explicit",
            })

    def test_launch_model_is_captured_when_no_explicit_model_is_given(self):
        with tempfile.TemporaryDirectory() as temporary:
            env = os.environ.copy()
            env["HERMES_TASKS_ROOT"] = temporary
            env["HERMES_INFERENCE_MODEL"] = "openai/launch-model"
            env["HERMES_INFERENCE_PROVIDER"] = "openai-codex"
            metadata = self.create_task(env)
            execution = metadata["extensions"]["remote_execution"]
            self.assertEqual(execution, {
                "model": "openai/launch-model", "model_source": "launch_env",
                "provider": "openai-codex", "provider_source": "launch_env",
            })

    def test_profile_config_default_is_captured_when_no_launch_model_exists(self):
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary) / "profile"
            profile.mkdir()
            (profile / "config.yaml").write_text(
                "model:\n  default: openai/config-model\n  provider: openai-codex\n", encoding="utf-8"
            )
            env = os.environ.copy()
            env["HERMES_TASKS_ROOT"] = str(Path(temporary) / "tasks")
            env["HERMES_HOME"] = str(profile)
            env.pop("HERMES_MODEL", None)
            env.pop("HERMES_INFERENCE_MODEL", None)
            env.pop("HERMES_TUI_PROVIDER", None)
            env.pop("HERMES_INFERENCE_PROVIDER", None)
            metadata = self.create_task(env)
            execution = metadata["extensions"]["remote_execution"]
            self.assertEqual(execution, {
                "model": "openai/config-model", "model_source": "profile_config",
                "provider": "openai-codex", "provider_source": "profile_config",
            })


if __name__ == "__main__":
    unittest.main()