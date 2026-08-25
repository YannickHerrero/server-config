from __future__ import annotations

import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import sys
import time
import unittest
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
FILES = ROOT / "files"

sys.path.insert(0, str(FILES))

import multica_project as project


def load_script(name: str, module_name: str):
    loader = importlib.machinery.SourceFileLoader(module_name, str(FILES / name))
    specification = importlib.util.spec_from_loader(module_name, loader)
    assert specification is not None
    module = importlib.util.module_from_spec(specification)
    loader.exec_module(module)
    return module


sync = load_script("multica-project-sync", "multica_project_sync")
config = load_script("multica-project-config", "multica_project_config")


class MulticaProcessTests(unittest.TestCase):
    def process_environment(self, state: Path, start: int) -> dict[str, str]:
        environment = os.environ.copy()
        environment.update(
            {
                "MULTICA_PROCESS_STATE": str(state),
                "MULTICA_PORT_MIN": str(start),
                "MULTICA_PORT_MAX": str(start + 29),
                "MULTICA_PORT_BLOCK_SIZE": "10",
            }
        )
        return environment

    def wait_for_state(self, state: Path) -> Path:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            matches = list(state.glob("*.json"))
            if matches:
                return matches[0]
            time.sleep(0.05)
        self.fail("multica-run did not create process state")

    def test_run_assigns_a_block_and_cleans_process_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "state"
            output = root / "port.txt"
            result = subprocess.run(
                [
                    sys.executable,
                    str(FILES / "multica-run"),
                    "run",
                    "--",
                    sys.executable,
                    "-c",
                    f"import os; open({str(output)!r}, 'w').write(os.environ['MULTICA_PORT_END'])",
                ],
                env=self.process_environment(state, 45000),
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_text(), "45009")
            self.assertEqual(list(state.glob("*.json")), [])

    def test_parallel_runs_receive_different_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "state"
            environment = self.process_environment(state, 45100)
            first = subprocess.Popen(
                [
                    sys.executable,
                    str(FILES / "multica-run"),
                    "run",
                    "--",
                    sys.executable,
                    "-c",
                    "import time; time.sleep(30)",
                ],
                env=environment,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                first_state_path = self.wait_for_state(state)
                first_state = json.loads(first_state_path.read_text())
                output = root / "second-port.txt"
                second = subprocess.run(
                    [
                        sys.executable,
                        str(FILES / "multica-run"),
                        "run",
                        "--",
                        sys.executable,
                        "-c",
                        f"import os; open({str(output)!r}, 'w').write(os.environ['MULTICA_PORT'])",
                    ],
                    env=environment,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertEqual(second.returncode, 0, second.stderr)
                self.assertNotEqual(int(output.read_text()), first_state["ports"][0])
            finally:
                first.terminate()
                first.wait(timeout=10)

    def test_stop_targets_a_registered_process_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state"
            environment = self.process_environment(state, 45200)
            wrapper = subprocess.Popen(
                [
                    sys.executable,
                    str(FILES / "multica-run"),
                    "run",
                    "--",
                    sys.executable,
                    "-c",
                    "import time; time.sleep(30)",
                ],
                env=environment,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            state_path = self.wait_for_state(state)
            run_id = json.loads(state_path.read_text())["run_id"]
            stopped = subprocess.run(
                [sys.executable, str(FILES / "multica-run"), "stop", run_id],
                env=environment,
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
            )
            self.assertEqual(stopped.returncode, 0, stopped.stderr)
            wrapper.wait(timeout=10)
            self.assertFalse(state_path.exists())


class MulticaProjectTests(unittest.TestCase):
    def test_canonical_remote_deduplicates_github_forms(self) -> None:
        expected = ("github.com/owner/repo", "https://github.com/Owner/Repo")
        self.assertEqual(project.canonical_remote("git@github.com:Owner/Repo.git"), expected)
        self.assertEqual(project.canonical_remote("ssh://git@github.com/Owner/Repo.git"), expected)
        self.assertEqual(project.canonical_remote("https://github.com/Owner/Repo.git"), expected)

    def test_discovery_finds_nested_repositories_without_build_trees(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outer = root / "outer"
            nested = outer / "packages" / "nested"
            ignored = outer / "node_modules" / "ignored"
            for path in (outer, nested, ignored):
                path.mkdir(parents=True, exist_ok=True)
                subprocess.run(["git", "init", "-q", str(path)], check=True)
            self.assertEqual(project.discover_repositories(root), [outer, nested])

    def test_policy_defaults_protect_host_configuration_repositories(self) -> None:
        policy = project.default_policy(
            Path("/home/yannick/dev/server-config"),
            "https://github.com/example/server-config",
            "main",
        )
        self.assertEqual(policy["autonomy"], "semi")
        self.assertEqual(policy["merge"]["mode"], "blocked")
        self.assertEqual(policy["deployment"]["target"], "blocked")
        project.validate_policy(policy)

    def test_policy_rejects_secret_like_keys(self) -> None:
        policy = project.default_policy(
            Path("repo"), "https://github.com/example/repo", "trunk"
        )
        policy["commands"]["release_token"] = "do not store this"
        with self.assertRaisesRegex(project.ProjectError, "secret-like"):
            project.validate_policy(policy)

    def test_existing_policy_is_not_rewritten_by_sync(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            policy_path = repository / project.POLICY_FILE
            policy_path.parent.mkdir()
            original = project.default_policy(
                repository, "https://github.com/example/repo", "trunk"
            )
            original["notes"] = ["keep this"]
            project.atomic_yaml(policy_path, original)
            before = policy_path.read_bytes()
            _path, created = project.ensure_policy(
                repository, "https://github.com/example/repo", "next"
            )
            self.assertFalse(created)
            self.assertEqual(policy_path.read_bytes(), before)

    def test_ephemeral_checkout_resolves_original_policy_from_map(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = root / "original"
            checkout = root / "checkout"
            for repository in (original, checkout):
                repository.mkdir()
                subprocess.run(["git", "init", "-q", str(repository)], check=True)
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(repository),
                        "remote",
                        "add",
                        "origin",
                        "git@github.com:Example/Repo.git",
                    ],
                    check=True,
                )
            policy_path = original / project.POLICY_FILE
            project.atomic_yaml(
                policy_path,
                project.default_policy(
                    original, "https://github.com/Example/Repo", "trunk"
                ),
            )
            state_path = root / "project-map.json"
            project.atomic_json(
                state_path,
                {
                    "version": 1,
                    "repositories": {
                        "github.com/example/repo": {
                            "path": str(original),
                            "project_id": "project-1",
                        }
                    },
                },
            )
            self.assertEqual(config.resolve_policy(checkout, state_path), policy_path)

    def test_dotted_update_validates_the_complete_policy(self) -> None:
        policy = project.default_policy(
            Path("repo"), "https://github.com/example/repo", "trunk"
        )
        updated = config.dotted_set(
            policy,
            "deployment.procedure",
            "multica-heavy-run -- docker compose build",
        )
        self.assertEqual(
            updated["deployment"]["procedure"],
            "multica-heavy-run -- docker compose build",
        )
        with self.assertRaisesRegex(project.ProjectError, "autonomy"):
            config.dotted_set(policy, "autonomy", "full")

    def test_resource_update_pins_ref_and_default_branch_hint(self) -> None:
        calls: list[list[str]] = []
        with (
            mock.patch.object(sync, "cli_json", side_effect=lambda args: calls.append(args) or {}),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            sync.ensure_resource(
                {"id": "project-1"},
                {
                    "id": "resource-1",
                    "resource_ref": {"url": "https://github.com/example/repo"},
                },
                "https://github.com/example/repo",
                "trunk",
                False,
            )
        self.assertEqual(len(calls), 1)
        self.assertIn("--ref", calls[0])
        self.assertIn("trunk", calls[0])
        self.assertIn("--default-branch-hint", calls[0])

    def test_atomic_policy_output_is_yaml_and_private(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "project.yaml"
            value = project.default_policy(
                Path("repo"), "https://github.com/example/repo", "main"
            )
            project.atomic_yaml(path, value)
            self.assertEqual(yaml.safe_load(path.read_text()), value)
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)


if __name__ == "__main__":
    unittest.main()
