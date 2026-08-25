# Global development workflow

Project-local `AGENTS.md`, `CLAUDE.md`, and release instructions override these defaults.

## Mandatory stages

Keep work in three separate stages unless the user explicitly asks to advance:

1. **Plan.** Inspect and propose behavior, affected files, risks, verification, and atomic commits. Do not edit files, build, test, commit, push, deploy, or release.
2. **Implement and test.** Begin only after explicit approval. Make small independently valid changes, run the documented verification, and create atomic commits. Do not push, deploy, or release.
3. **Release.** Begin only after an explicit request to push, publish, deploy, upload, or release. Run the release preflight and publish only the intended commits or artifacts.

At the end of each stage, state the result and the exact action needed to advance.

## Skills

- Load and follow `three-stage-workflow` for feature requests, bug fixes, repository changes, commits, pushes, and releases.
- Always load and apply `unslop` before producing user-facing writing.
- Read a skill completely when its description matches the task. Resolve its relative files from the skill directory.
- Skills supplement these instructions. They do not override project-local rules.

## Git and safety

- Before editing or committing, inspect `git status --short`. Never overwrite, stage, restore, or commit unrelated user changes.
- Make small atomic conventional commits. Keep one logical change per commit and run the project verification before each commit.
- Never amend.
- Never force-push unless the user explicitly authorizes a specific history rewrite after a verified backup and preflight. Always use `--force-with-lease`, never `--force`.
- Never push or release without explicit approval in the current session.
- The user prefers completed changes to be pushed. Proactively request push approval after implementation. Push approval does not authorize a deployment or release.
- Never commit or print passwords, tokens, private keys, authentication files, session data, or other secrets.
- Read and obey project instructions before changing code.

## Machine configuration

`~/dev/server-config` is the source of truth for persistent configuration on this machine.

Before changing a system package, global CLI, runtime, user configuration, file under `/etc`, service, user or group membership, firewall rule, SSH setting, Android SDK component, or other machine-wide state:

1. Inspect `~/dev/server-config` and its `AGENTS.md`.
2. Change the Ansible configuration or a tracked source file.
3. Run `./bin/validate`.
4. Run `./bin/check` and review the diff.
5. Obtain explicit approval before `./bin/apply`, or confirm that the user opened an active maintenance window whose scope covers the change.
6. Apply directly only after explicit approval. During a maintenance window, request application only through `server-config-window converge`.
7. Run `./bin/check` again. It must report `changed=0`; the broker enforces this during a maintenance window.
8. Run `./bin/doctor`; the broker enforces this during a maintenance window.
9. Commit the change atomically before requesting brokered convergence.

When asking the user to run Ansible, `./bin/check`, or `./bin/apply`, offer in the same message to handle the work through a maintenance window. State whether a normal or sensitive window is required. If a suitable window is already active, use `server-config-window converge` yourself instead of asking the user to run those commands.

A maintenance window is standing application approval only until its displayed deadline. Never open or extend one on the user's behalf. Confirm its scope with `server-config-window status`. A normal window blocks access, firewall, SSH, Tailscale, sudo, user-account, Citadel, and maintenance-window tasks. The user must open a sensitive window to authorize host-access categories. Citadel and maintenance-window changes always use the ordinary interactive apply path. A window does not authorize pushing or releasing commits.

Do not make persistent changes directly with `apt install`, global npm installs, `mise use -g`, installer pipes, edits under `/etc`, or edits to managed files in `$HOME`.

Project-specific dependencies belong in the project's own manifest and lockfile, not in `server-config`.

Authentication, secrets, sessions, histories, caches, temporary diagnostics, and emergency recovery are not managed by Ansible. Reconcile any persistent emergency change into `server-config` immediately after access is restored.

If `server-config` is unavailable or has unrelated changes, stop and ask before changing the machine.

## Project-local operational configuration

- Before asking for recurring release or service configuration, inspect the project's documented ignored local config files and external credential locations.
- When the user provides reusable project-specific configuration, persist it in the project's documented ignored local file so future agents can use it without asking again.
- Persist only non-secret metadata in project-local config. Keep credentials and private keys outside the repository at the documented secure location.
- Confirm that local config is ignored before writing it, apply restrictive permissions, and validate from a clean shell without relying on another project's environment or an earlier shell session.
- If the project has no documented ignored config or credential location, propose one and obtain approval before storing sensitive configuration.

## Verification

- Use the project's documented build and test commands. Report real results, not assumptions.
- Perform available visual verification after UI changes.
- Distinguish automated evidence from interactions that require manual testing, such as gestures, system dialogs, audio, video, and native menu behavior.
- Finish implementation and release reports with the actual Git status.
