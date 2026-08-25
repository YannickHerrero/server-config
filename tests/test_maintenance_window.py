#!/usr/bin/env python3
from __future__ import annotations

import importlib.machinery
import importlib.util
import io
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import sys
import threading
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "files/server-config-window"
loader = importlib.machinery.SourceFileLoader("server_config_window", str(SOURCE))
spec = importlib.util.spec_from_loader(loader.name, loader)
assert spec is not None
window = importlib.util.module_from_spec(spec)
sys.modules[loader.name] = window
loader.exec_module(window)


class MaintenanceWindowTests(unittest.TestCase):
    def config(self, root: Path, *, sensitive: bool = False):
        account = pwd.getpwuid(os.getuid())
        return window.BrokerConfig(
            authorization=window.Authorization(seconds=3600, allow_sensitive=sensitive),
            user=account.pw_name,
            uid=account.pw_uid,
            gid=account.pw_gid,
            home=Path(account.pw_dir),
            repo=root,
            controller_unit=f"citadel@{account.pw_name}.service",
            socket_path=root / "window.sock",
            log_dir=root / "logs",
        )

    def test_duration_is_bounded_at_eight_hours(self):
        self.assertEqual(window.authorization_for(480, False).seconds, 8 * 60 * 60)
        self.assertEqual(window.parse_authorization("28800-sensitive").seconds, 8 * 60 * 60)
        with self.assertRaises(window.WindowError):
            window.authorization_for(481, False)
        with self.assertRaises(window.WindowError):
            window.authorization_for(0, False)
        with self.assertRaises(window.WindowError):
            window.parse_authorization("28801-safe")

    def test_safe_scope_skips_sensitive_and_self_modifying_tasks(self):
        tags = window.skipped_tags(False)
        self.assertIn("maintenance-window", tags)
        self.assertIn("citadel", tags)
        self.assertIn("access", tags)
        self.assertIn("firewall", tags)
        self.assertIn("ssh", tags)
        self.assertIn("tailscale", tags)

    def test_sensitive_scope_still_protects_controller_and_broker(self):
        self.assertEqual(window.skipped_tags(True), ("citadel", "maintenance-window"))

    def test_broker_uses_explicit_inventory_user_and_mode(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = self.config(Path(temporary), sensitive=False)
            command = window.ansible_command(config, check=True)
        self.assertIn("--check", command)
        self.assertIn("--diff", command)
        self.assertIn("server_config_maintenance_broker=true", command)
        self.assertIn(f"server_config_managed_user={config.user}", command)
        skipped = command[command.index("--skip-tags") + 1].split(",")
        self.assertIn("maintenance-window", skipped)
        self.assertIn("citadel", skipped)

    def test_repo_preflight_accepts_clean_main_ahead_of_origin(self):
        commit = "a" * 40
        responses = iter(
            [
                (0, "", ""),
                (0, "main\n", ""),
                (0, "origin/main\n", ""),
                (0, "0\t2\n", ""),
                (0, f"{commit}\n", ""),
            ]
        )

        def capture(_config, command):
            returncode, stdout, stderr = next(responses)
            return subprocess.CompletedProcess(command, returncode, stdout, stderr)

        with tempfile.TemporaryDirectory() as temporary:
            config = self.config(Path(temporary))
            self.assertEqual(window.require_repo_state(config, capture=capture), commit)

    def test_repo_preflight_rejects_dirty_or_behind_checkout(self):
        dirty = lambda _config, command: subprocess.CompletedProcess(command, 0, " M playbook.yml\n", "")
        with tempfile.TemporaryDirectory() as temporary:
            config = self.config(Path(temporary))
            with self.assertRaisesRegex(window.WindowError, "clean worktree"):
                window.require_repo_state(config, capture=dirty)

        responses = iter(
            [
                (0, "", ""),
                (0, "main\n", ""),
                (0, "origin/main\n", ""),
                (0, "1\t0\n", ""),
            ]
        )

        def behind(_config, command):
            returncode, stdout, stderr = next(responses)
            return subprocess.CompletedProcess(command, returncode, stdout, stderr)

        with tempfile.TemporaryDirectory() as temporary:
            config = self.config(Path(temporary))
            with self.assertRaisesRegex(window.WindowError, "behind or diverged"):
                window.require_repo_state(config, capture=behind)

    def test_command_runner_captures_output_and_enforces_deadline(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (root / "command.log").open("wb") as log_file:
                result = window.run_command(
                    ["/bin/sh", "-c", "printf ready"],
                    cwd=root,
                    environment=os.environ.copy(),
                    deadline=time.monotonic() + 5,
                    connection=None,
                    log_file=log_file,
                    label="Test",
                )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.output, "ready")

            started = time.monotonic()
            with (root / "timeout.log").open("wb") as log_file:
                result = window.run_command(
                    ["/bin/sh", "-c", "sleep 5"],
                    cwd=root,
                    environment=os.environ.copy(),
                    deadline=time.monotonic() + 0.1,
                    connection=None,
                    log_file=log_file,
                    label="Timeout",
                )
            self.assertTrue(result.timed_out)
            self.assertLess(time.monotonic() - started, 2)

    def test_convergence_recap_requires_changed_zero(self):
        passing = "localhost : ok=10 changed=0 unreachable=0 failed=0 skipped=1 rescued=0 ignored=0"
        failing = "localhost : ok=10 changed=1 unreachable=0 failed=0 skipped=1 rescued=0 ignored=0"
        self.assertIsNotNone(window.RECAP_RE.search(passing))
        self.assertIsNone(window.RECAP_RE.search(failing))

    def test_systemd_template_preserves_expiry_and_controller_boundaries(self):
        content = (ROOT / "templates/server-config-maintenance-window@.service.j2").read_text()
        self.assertIn("RuntimeMaxSec={{ server_config_maintenance_window_max_minutes }}m", content)
        self.assertIn("ExecStartPre=/usr/bin/systemctl stop citadel@", content)
        self.assertIn("ExecStopPost=/usr/local/bin/server-config-window restore-controller", content)
        self.assertIn("--controller-unit citadel@", content)
        self.assertIn("RuntimeDirectoryMode=0750", content)
        self.assertNotIn("NOPASSWD", content)

        account = pwd.getpwuid(os.getuid())
        replacements = {
            "{{ server_config_repo_dir }}": str(ROOT),
            "{{ ansible_user_id }}": account.pw_name,
            "{{ ansible_user_uid }}": str(account.pw_uid),
            "{{ ansible_user_gid }}": str(account.pw_gid),
            "{{ ansible_user_dir }}": account.pw_dir,
            "{{ server_config_maintenance_window_max_minutes }}": "480",
            "/usr/local/bin/server-config-window": str(SOURCE),
        }
        for old, new in replacements.items():
            content = content.replace(old, new)
        self.assertNotIn("{{", content)

        systemd_analyze = shutil.which("systemd-analyze")
        if systemd_analyze is None:
            self.skipTest("systemd-analyze is unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            unit = Path(temporary) / "server-config-maintenance-window@.service"
            unit.write_text(content)
            result = subprocess.run(
                [systemd_analyze, "verify", str(unit)],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_broker_uses_a_nonblocking_global_window_lock(self):
        with tempfile.TemporaryDirectory() as temporary:
            lock_path = Path(temporary) / "window.lock"
            descriptor = window.acquire_window_lock(lock_path)
            try:
                with self.assertRaisesRegex(window.WindowError, "another server-config"):
                    window.acquire_window_lock(lock_path)
            finally:
                os.close(descriptor)

    def test_daemon_accepts_the_managed_user_and_root_opener(self):
        self.assertTrue(window.peer_is_authorized(1000, 1000))
        self.assertTrue(window.peer_is_authorized(0, 1000))
        self.assertFalse(window.peer_is_authorized(1001, 1000))

    def test_client_streams_output_and_requires_a_final_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            socket_path = Path(temporary) / "window.sock"
            listener = window.socket.socket(window.socket.AF_UNIX, window.socket.SOCK_STREAM)
            listener.bind(str(socket_path))
            listener.listen(1)

            def serve():
                connection, _ = listener.accept()
                with connection:
                    request = connection.recv(4096)
                    self.assertIn(b'"command": "status"', request)
                    window.send_message(connection, {"type": "output", "data": "checked\n"})
                    window.send_message(connection, {"type": "result", "ok": True, "message": "open"})
                listener.close()

            thread = threading.Thread(target=serve)
            thread.start()
            output = io.StringIO()
            with window.contextlib.redirect_stdout(output):
                result = window.request("status", socket_path)
            thread.join(timeout=2)
            self.assertFalse(thread.is_alive())
            self.assertEqual(output.getvalue(), "checked\n")
            self.assertTrue(result["ok"])

    def test_client_reports_a_reset_without_a_traceback(self):
        with tempfile.TemporaryDirectory() as temporary:
            socket_path = Path(temporary) / "window.sock"
            listener = window.socket.socket(window.socket.AF_UNIX, window.socket.SOCK_STREAM)
            listener.bind(str(socket_path))
            listener.listen(1)

            def reset():
                connection, _ = listener.accept()
                connection.close()
                listener.close()

            thread = threading.Thread(target=reset)
            thread.start()
            with self.assertRaisesRegex(window.WindowError, "without a result"):
                window.request("status", socket_path)
            thread.join(timeout=2)
            self.assertFalse(thread.is_alive())

    def test_every_privileged_ansible_task_names_root_explicitly(self):
        for path in [ROOT / "playbook.yml", *ROOT.glob("tasks/*.yml")]:
            lines = path.read_text().splitlines()
            for index, line in enumerate(lines):
                if line.strip() == "become: true":
                    self.assertEqual(lines[index + 1].strip(), "become_user: root", f"{path}:{index + 1}")

    def test_active_window_guard_allows_read_only_check_mode(self):
        content = (ROOT / "tasks/maintenance-window.yml").read_text()
        guard = content.split("- name: Refuse to replace an active maintenance-window broker", 1)[1]
        guard = guard.split("- name: Require a bounded maintenance-window duration", 1)[0]
        self.assertIn("when: not ansible_check_mode", guard)

    def test_policy_does_not_install_passwordless_sudo(self):
        tracked_sources = [ROOT / "playbook.yml", *ROOT.glob("tasks/*.yml"), *ROOT.glob("templates/*")]
        combined = "\n".join(path.read_text() for path in tracked_sources)
        self.assertNotIn("NOPASSWD", combined)
        self.assertNotIn("sudoers.d", combined)


if __name__ == "__main__":
    unittest.main()
