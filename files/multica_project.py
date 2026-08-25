#!/usr/bin/env python3
"""Shared project discovery and local policy helpers for Multica."""

from __future__ import annotations

import contextlib
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any, Iterator, Mapping, Sequence
from urllib.parse import urlparse

import yaml

POLICY_FILE = Path(".multica/project.yaml")
STATE_VERSION = 1
SECRET_KEY = re.compile(
    r"(?:^|_)(?:api_?key|auth|credential|jwt|password|private_?key|secret|session|token)(?:$|_)",
    re.IGNORECASE,
)
ALLOWED_POLICY_KEYS = {
    "schema",
    "repository",
    "autonomy",
    "merge",
    "qa",
    "deployment",
    "commands",
    "notes",
}
SKIPPED_DIRECTORIES = {
    ".cache",
    ".git",
    ".gradle",
    ".next",
    ".turbo",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
}


class ProjectError(RuntimeError):
    """A project helper cannot continue without risking the wrong repository."""


def run(
    argv: Sequence[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
    environment: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if environment:
        env.update(environment)
    result = subprocess.run(
        list(argv),
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
        raise ProjectError(f"{' '.join(argv)}: {detail}")
    return result


def canonical_remote(raw: str) -> tuple[str, str]:
    """Return a stable identity and a cloneable HTTPS URL."""
    value = raw.strip()
    if not value:
        raise ProjectError("repository remote is empty")

    scp_match = re.fullmatch(r"(?:[^@/]+@)?([^:/]+):(.+)", value)
    if scp_match and "://" not in value:
        host = scp_match.group(1).lower()
        path = scp_match.group(2)
    else:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https", "ssh", "git"} or not parsed.hostname:
            raise ProjectError(f"unsupported repository remote: {raw}")
        host = parsed.hostname.lower()
        path = parsed.path

    path = path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    if not path or "/" not in path:
        raise ProjectError(f"repository remote has no owner and name: {raw}")
    identity = f"{host}/{path}".lower()
    return identity, f"https://{host}/{path}"


def git_output(repository: Path, *arguments: str, check: bool = True) -> str:
    result = run(["git", "-C", str(repository), *arguments], check=check)
    return result.stdout.strip()


def discover_repositories(root: Path) -> list[Path]:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise ProjectError(f"development root is not a directory: {root}")

    repositories: set[Path] = set()
    for current, directory_names, file_names in os.walk(root, followlinks=False):
        directory_names[:] = [
            name for name in directory_names if name not in SKIPPED_DIRECTORIES
        ]
        marker_present = ".git" in file_names or (Path(current) / ".git").is_dir()
        if not marker_present:
            continue
        result = run(
            ["git", "-C", current, "rev-parse", "--show-toplevel"],
            check=False,
        )
        if result.returncode == 0:
            repositories.add(Path(result.stdout.strip()).resolve())
    return sorted(repositories)


def repository_remote(repository: Path) -> tuple[str, str] | None:
    result = run(
        ["git", "-C", str(repository), "remote", "get-url", "origin"],
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return canonical_remote(result.stdout)


def default_branch(repository: Path, canonical_url: str) -> str:
    github = run(
        ["gh", "repo", "view", canonical_url, "--json", "defaultBranchRef"],
        check=False,
    )
    if github.returncode == 0:
        try:
            name = json.loads(github.stdout).get("defaultBranchRef", {}).get("name", "")
        except (json.JSONDecodeError, AttributeError):
            name = ""
        if isinstance(name, str) and name.strip():
            return name.strip()

    symbolic = run(
        [
            "git",
            "-C",
            str(repository),
            "symbolic-ref",
            "--quiet",
            "--short",
            "refs/remotes/origin/HEAD",
        ],
        check=False,
    )
    if symbolic.returncode == 0 and symbolic.stdout.strip().startswith("origin/"):
        return symbolic.stdout.strip().removeprefix("origin/")

    remote_head = run(
        ["git", "-C", str(repository), "ls-remote", "--symref", "origin", "HEAD"],
        check=False,
    )
    for line in remote_head.stdout.splitlines():
        match = re.fullmatch(r"ref:\s+refs/heads/(.+)\s+HEAD", line)
        if match:
            return match.group(1)
    raise ProjectError(f"cannot determine the default branch for {repository}")


def parse_resource_ref(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def default_policy(repository: Path, remote: str, branch: str) -> dict[str, Any]:
    sensitive = repository.name in {"citadel", "server-config"}
    return {
        "schema": 1,
        "repository": {"remote": remote, "default_branch": branch},
        "autonomy": "semi" if sensitive else "auto",
        "merge": {"mode": "blocked" if sensitive else "reviewed"},
        "qa": {"web": "auto", "android": "when_configured"},
        "deployment": {
            "target": "blocked" if sensitive else "discover",
            "procedure": None,
            "verify": [],
        },
        "commands": {},
        "notes": [],
    }


def _walk_keys(value: Any, path: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            yield (*path, key_text), child
            yield from _walk_keys(child, (*path, key_text))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_keys(child, (*path, str(index)))


def validate_policy(policy: Any) -> dict[str, Any]:
    if not isinstance(policy, dict):
        raise ProjectError("project policy must be a YAML object")
    unknown = set(policy) - ALLOWED_POLICY_KEYS
    if unknown:
        raise ProjectError(f"unsupported project policy keys: {', '.join(sorted(unknown))}")
    if policy.get("schema") != 1:
        raise ProjectError("project policy schema must be 1")
    if policy.get("autonomy") not in {"auto", "semi"}:
        raise ProjectError("autonomy must be auto or semi")

    merge = policy.get("merge", {})
    if not isinstance(merge, dict) or merge.get("mode") not in {
        "auto",
        "blocked",
        "manual",
        "reviewed",
    }:
        raise ProjectError("merge.mode must be auto, reviewed, manual, or blocked")

    repository = policy.get("repository", {})
    if not isinstance(repository, dict):
        raise ProjectError("repository must be a YAML object")
    if not isinstance(repository.get("remote"), str):
        raise ProjectError("repository.remote must be a string")
    if not isinstance(repository.get("default_branch"), str):
        raise ProjectError("repository.default_branch must be a string")

    deployment = policy.get("deployment", {})
    if not isinstance(deployment, dict) or not isinstance(deployment.get("target"), str):
        raise ProjectError("deployment.target must be a string")
    procedure = deployment.get("procedure")
    if procedure is not None and not isinstance(procedure, str):
        raise ProjectError("deployment.procedure must be a string or null")
    verify = deployment.get("verify", [])
    if not isinstance(verify, list) or not all(isinstance(item, str) for item in verify):
        raise ProjectError("deployment.verify must be a list of commands")

    commands = policy.get("commands", {})
    if not isinstance(commands, dict):
        raise ProjectError("commands must be a YAML object")
    for name, command in commands.items():
        if not isinstance(name, str) or not isinstance(command, (str, list)):
            raise ProjectError("commands values must be strings or argument lists")
        if isinstance(command, list) and not all(isinstance(item, str) for item in command):
            raise ProjectError("command argument lists may contain only strings")

    for path, _value in _walk_keys(policy):
        if any(SECRET_KEY.search(component) for component in path):
            raise ProjectError(f"secret-like policy key is forbidden: {'.'.join(path)}")
    return policy


def load_policy(path: Path) -> dict[str, Any]:
    try:
        policy = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ProjectError(f"cannot read {path}: {error}") from error
    return validate_policy(policy)


def atomic_yaml(path: Path, value: dict[str, Any]) -> None:
    validate_policy(value)
    path.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            yaml.safe_dump(value, handle, sort_keys=False, allow_unicode=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o640)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def ensure_policy(repository: Path, remote: str, branch: str) -> tuple[Path, bool]:
    path = repository / POLICY_FILE
    if path.exists():
        load_policy(path)
        return path, False
    atomic_yaml(path, default_policy(repository, remote, branch))
    return path, True


def atomic_json(path: Path, value: Any, mode: int = 0o600) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_state(path: Path) -> dict[str, Any]:
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"version": STATE_VERSION, "repositories": {}}
    except (OSError, json.JSONDecodeError) as error:
        raise ProjectError(f"cannot read project map {path}: {error}") from error
    if state.get("version") != STATE_VERSION or not isinstance(state.get("repositories"), dict):
        raise ProjectError(f"unsupported project map format: {path}")
    return state


@contextlib.contextmanager
def locked(path: Path) -> Iterator[None]:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def project_map_entry(state: dict[str, Any], repository: Path) -> tuple[str, dict[str, Any]]:
    remote = repository_remote(repository)
    if remote is None:
        raise ProjectError(f"repository has no origin remote: {repository}")
    identity, _canonical = remote
    entry = state["repositories"].get(identity)
    if not isinstance(entry, dict):
        raise ProjectError(f"repository is absent from the Multica project map: {identity}")
    original = Path(str(entry.get("path", ""))).expanduser().resolve()
    if not original.is_dir():
        raise ProjectError(f"mapped repository path is unavailable: {original}")
    return identity, entry


def now_utc() -> str:
    return dt.datetime.now(dt.UTC).isoformat()
