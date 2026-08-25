from __future__ import annotations

import contextlib
import importlib.machinery
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
FILES = ROOT / "files"

import sys
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
