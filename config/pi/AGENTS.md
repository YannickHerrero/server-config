# Global development workflow

Project-local `AGENTS.md`, `CLAUDE.md`, and release instructions override these defaults.

## Mandatory stages

Keep work in three separate stages unless the user explicitly asks to advance:

1. Plan. Inspect and propose behavior, affected files, risks, verification, and atomic commits. Do not modify files, run builds or tests, commit, push, deploy, or release.
2. Implement and test. Begin only after explicit approval. Make small independently valid changes, run the documented verification, and create atomic commits. Do not push, deploy, or release.
3. Release. Begin only after an explicit request to push, publish, deploy, upload, or release.

At the end of each stage, state the result and the exact action needed to advance.

## Git and safety

- Inspect `git status --short` before edits, tests, applications, and commits.
- Never overwrite, stage, restore, or commit unrelated changes.
- Keep one logical change per conventional commit. Never amend.
- Never force-push unless the user authorizes a specific rewrite after a verified backup. Use `--force-with-lease`, never `--force`.
- Never push or release without explicit approval in the current session.
- Never commit or print passwords, tokens, private keys, authentication files, session data, or other secrets.

## Machine configuration

`~/dev/server-config` is the source of truth for persistent configuration on this machine.

Before changing a system package, global CLI, runtime, user configuration, file under `/etc`, service, user or group membership, firewall rule, SSH setting, Android SDK component, or other machine-wide state:

1. Inspect `~/dev/server-config` and its `AGENTS.md`.
2. Change the Ansible configuration or a tracked source file.
3. Run `./bin/validate`.
4. Run `./bin/check` and review the diff.
5. Obtain explicit approval before `./bin/apply`.
6. Apply the change.
7. Run `./bin/check` again. It must report `changed=0`.
8. Run `./bin/doctor`.
9. Commit the change atomically.

Do not make persistent changes directly with `apt install`, global npm installs, `mise use -g`, installer pipes, edits under `/etc`, or edits to managed files in `$HOME`.

Project-specific dependencies belong in the project's own manifest and lockfile, not in `server-config`.

Authentication, secrets, sessions, histories, caches, temporary diagnostics, and emergency recovery are not managed by Ansible. Any persistent emergency change must be reconciled into `server-config` immediately after access is restored.

If `server-config` is unavailable or has unrelated changes, stop and ask before changing the machine.

## Operational configuration

- Inspect documented ignored local configuration and credential locations before asking for recurring values.
- Persist reusable non-secret metadata in the project's documented ignored local file.
- Keep credentials at the documented secure location with restrictive permissions.
- Do not rely on another project's environment or an earlier shell session when validating configuration.

## Verification

- Run the project's documented build and test commands and report actual results.
- Distinguish automated evidence from checks that require human interaction.
- Finish implementation and release reports with the actual Git status.
