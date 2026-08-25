# Multica operations

This host runs the Multica service and its Pi agents as `yannick`. The server, agents, and ordinary development commands share Yannick's rootless Docker daemon, GitHub login, repositories, and Unix permissions. The agents therefore have the same access to local credentials, LXD, and maintenance windows as other processes owned by `yannick`.

Pi configuration remains separate under `~/.pi/multica`. The agent runtime does not load Yannick's global `AGENTS.md`, personal skills, extensions, prompts, or themes.

Raw Multica ports bind to loopback. Citadel publishes the single-origin proxy on Tailscale HTTPS port `8444`. Do not add a public listener or enable Funnel.

## Managed paths

| Purpose | Path |
| --- | --- |
| Pinned server checkout | `~/.local/share/multica/server` |
| Private server environment | `~/.config/multica/server.env` |
| Agent CLI profile | `~/.multica/config.json` |
| Agent Pi profile | `~/.pi/multica` |
| Task workspaces | `~/.local/share/multica/workspaces` |
| Repo-to-project map | `~/.local/state/multica/project-map.json` |
| Local project memory | `~/dev/<repo>/.multica/project.yaml` |
| Process and port locks | `~/.local/state/multica/processes` |
| Android SDK | `/opt/android-sdk` |

The global Git exclude file ignores `.multica/`. The files remain untracked, but `git add -f` can still override an ignore rule. Winter checks every PR for that mistake.

## First activation

Application needs explicit approval because it installs host packages, adds Yannick to the KVM group, and starts rootless Docker. It also removes any retired `multica` account and ACLs left by an earlier installation. Apply only a committed `server-config` checkout:

```bash
./bin/check
./bin/apply
./bin/check               # must report changed=0
```

The first Android application downloads an x86-64 system image of about 1.7 GB. It does not boot the emulator.

Prepare the committed Citadel catalog before restarting the controller:

```bash
cd ~/dev/citadel
pnpm install --frozen-lockfile
pnpm lint
pnpm test
pnpm build
pnpm ops:render config/citadel.local.json
pnpm ops:routes config/citadel.local.json
```

Review the Supervisor files and route plan. With separate activation approval, update Supervisor and apply only the planned route:

```bash
supervisorctl -c ~/.local/state/citadel/supervisord.conf reread
supervisorctl -c ~/.local/state/citadel/supervisord.conf update
pnpm ops:routes config/citadel.local.json --apply
```

Confirm the containers and private proxy:

```bash
multica-server ps
multica-server health
```

Open `https://<this-node-tailscale-dns-name>:8444` from another tailnet device. Request the initial login code, then read only the latest code:

```bash
multica-server verification-code
```

The backend prints the code because no email provider is configured. Do not paste it into an issue or an agent task.

## Agent Pi profile

The agents reuse Yannick's GitHub CLI identity:

```bash
gh auth status
git config --global user.name
git config --global user.email
```

They use a separate Pi configuration. Launch that profile, run `/login`, complete OAuth, then exit Pi. Confirm that its authentication file uses mode `0600`:

```bash
PI_CODING_AGENT_DIR="$HOME/.pi/multica" pi
stat -c '%a %n' "$HOME/.pi/multica/auth.json"
```

Configure the private Multica origin and authenticate the CLI:

```bash
origin="https://$(tailscale status --json | jq -r '.Self.DNSName | rtrimstr(".")'):8444"
multica config set server_url "$origin"
multica config set app_url "$origin"
multica login
```

Start the system-managed daemon and confirm the Pi runtime is online:

```bash
sudo systemctl start multica-daemon.service
multica daemon status
```

The service refuses to start before `~/.multica/config.json` exists. It has a global concurrency limit of three tasks and cannot update its own CLI.

## Workspace, agents, and projects

After the runtime is online, provision the Dev workspace and agents:

```bash
multica-bootstrap
```

The command is idempotent. It creates or updates:

- workspace `Dev`, slug `dev`, issue prefix `DEV`;
- Karina with concurrency `2`;
- Giselle, Winter, and Ningning with concurrency `1`;
- Pi arguments `--approve`, `--no-extensions`, `--no-prompt-templates`, and `--no-themes`.

It keeps context files and Multica's runtime skills enabled. The separate `~/.pi/multica` directory has no link to the personal skills or three-stage workflow under `~/.pi/agent`.

Project synchronization runs at 08:00 and 20:00 `Europe/Paris`:

```bash
systemctl list-timers multica-project-sync.timer
sudo systemctl start multica-project-sync.service
journalctl -u multica-project-sync.service
```

The sync command discovers Git repos below `~/dev`, normalizes their `origin`, asks GitHub for the default branch, creates missing Multica projects, and attaches `github_repo` resources. Repos with no `origin` are reported and skipped. It never assumes `main`.

`server-config` and `citadel` start with `autonomy: semi`, blocked merges, and blocked deployments. Other repos start with `autonomy: auto` and reviewed merges. Existing `project.yaml` files are validated but never overwritten by synchronization.

Inspect or update project memory from an original checkout or a temporary task worktree:

```bash
multica-project-config path
multica-project-config get deployment
multica-project-config set deployment.procedure '"multica-heavy-run -- docker compose up --build"'
multica-project-config set deployment.verify '["curl --fail http://127.0.0.1:8080/health"]'
multica-project-config validate
```

The helper rejects unsupported top-level fields and secret-like keys. Keep credentials in each provider's official local credential store, not in this YAML.

## Ports and owned processes

Agents must place processes under `multica-run`. Use `run` for a bounded foreground command and `start` for a managed server that must survive across tool calls:

```bash
multica-run run -- npm test
multica-run start -- npm run dev
multica-run list
multica-run logs <run-id>
multica-run stop <run-id>
```

Each run holds a ten-port block in `41000-41999` and exports `PORT`, `MULTICA_PORT`, `MULTICA_PORT_BASE`, and `MULTICA_PORT_END`. `stop` validates the PID owner, process start time, and process group before sending a signal.

Serialize CPU and memory heavy setup steps:

```bash
multica-heavy-run -- pnpm exec playwright test
multica-heavy-run -- ./gradlew test
multica-heavy-run -- docker build .
```

Do not add `&`, `nohup` or a daemon flag behind either wrapper. `multica-run start` is the supported detached mode and keeps PID, log, process-group, and port ownership.

## Android QA

The managed AVD is `multica-api-35`. Start it as an owned foreground process, wait for boot, test, then stop only that run:

```bash
multica-run start -- multica-android-emulator start
multica-android-emulator wait 180
multica-android-emulator status
multica-android-emulator screenshot artifacts/android.png
multica-android-emulator logcat -d
multica-android-emulator stop
```

Use `multica-heavy-run` for Gradle and emulator startup work. The helper prevents a second managed emulator from starting. Gestures, system dialogs, audio, video, and native menu behavior still need manual confirmation when the automated test cannot observe them.

## Updates and recovery

Update Multica only by changing its version, commit, CLI checksum, image tags, and any Compose changes in `server-config`. Do not run the Multica self-updater. Update Docker and Android command-line tools the same way with reviewed checksums.

Useful diagnostics:

```bash
multica-server ps
multica-server logs backend
sudo journalctl -u multica-daemon.service
sudo journalctl -u server-config-docker@yannick.service
./bin/doctor
```

Stopping the stack preserves its Docker volumes:

```bash
multica-server down
```

Never add `--volumes` during routine recovery. The PostgreSQL and upload volumes contain Multica's durable state. This setup does not provide an off-host backup. Configure one before treating Multica as the only copy of issue history or deployment procedures.
