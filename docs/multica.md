# Multica host boundary

`server-config` installs the host capabilities required by Multica:

- pinned rootless Docker Engine, Compose, and Buildx;
- the rootlesskit AppArmor profile and bridge netfilter module;
- Java 21, Android command-line tools, API 35, the x86-64 system image, and KVM access;
- Citadel and its maintenance-window broker.

The local `~/dev/multica` repository owns everything application-specific. This includes the CLI checksum, image digests, Compose and Caddy files, private environment, Pi profile settings, agents, project synchronization, Android virtual device, helper commands, tests, and operations runbook.

Credentials remain outside both repositories under `~/.multica`, `~/.pi/multica`, and ignored project-local files.

## Migration cleanup

The playbook retires the old host-managed units and commands:

- `multica-daemon.service`;
- `multica-project-sync.service` and `.timer`;
- `/usr/local/bin/multica*`;
- `/opt/server-config/multica`;
- `~/.local/bin/multica-server`.

It keeps `~/.local/share/multica/server` and `~/.config/multica/server.env` for rollback. Remove those paths only after the project-owned deployment, its named Docker volumes, Citadel health check, agent daemon, and scheduler have all passed their activation checks.

Do not apply this cleanup before `~/dev/multica` has imported the existing secrets and Citadel has rendered the project-owned service definitions. Activation requires separate approval and a maintenance window.
