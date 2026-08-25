# Development workflow

This repository configures mutable Ubuntu development servers with Ansible. Keep it small and readable.

## Stages

Work in three separate stages unless the user explicitly asks to continue:

1. Plan. Inspect and describe behavior, files, risks, verification, and commits. Do not edit or run changes.
2. Implement and test. Edit, validate, apply only when authorized, and create atomic commits. Do not push.
3. Release. Push only after explicit approval in the current session.

## Safety

- Inspect `git status --short` before edits, tests, applications, and commits.
- Never overwrite, stage, restore, or commit unrelated changes.
- Never commit passwords, tokens, private keys, authentication files, session data, public server addresses, or private inventory.
- Keep reusable secrets outside the repository. Authentication for Pi, GitHub, and infrastructure services stays interactive.
- Do not edit managed files under `/etc` directly. Change the playbook or a template, inspect the diff, then apply it.
- Do not grant passwordless sudo to Ansible, Pi, or another agent.
- Do not change SSH, sudo, networking, or firewall rules without explicit approval and a tested recovery path.
- A maintenance window opened interactively by the user is standing approval for brokered convergence within that window's scope. The agent must never open or extend a window.
- Do not run `pi update` directly. Change the pinned version in `group_vars/all.yml`, validate, and apply.

## Commands

- `./bin/validate` checks shell, YAML, and Ansible files without changing the host.
- `./bin/check` shows the changes Ansible would make.
- `./bin/apply` validates and applies the playbook after sudo approval.
- `./bin/doctor` reports host, RAID, storage, update, runtime, and KVM state without changing it.

After an application, run `./bin/check` again. A converged host should report `changed=0`.

During an active maintenance window, use only `server-config-window converge`. The broker enforces validation, a dry run, application, `changed=0`, and doctor. It requires a clean committed `main`, refuses a checkout behind `origin/main`, and records root-owned logs. A normal window blocks access, firewall, SSH, Tailscale, sudo, user-account, Citadel, and broker tasks. The user must open a sensitive window to authorize host-access categories. Citadel and broker updates always require the ordinary interactive apply path.

## Design rules

- Support Ubuntu Server 24.04 LTS on x86-64 first.
- Prefer built-in Ansible modules. Add collections or roles only after the single playbook becomes hard to maintain.
- Pin downloaded runtimes and verify their checksums.
- Let APT manage security package versions. Do not pin distribution packages.
- Add a tool only after a real use requires it.
- Keep one logical change per conventional commit. Never amend or force-push.
