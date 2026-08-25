# server-config

Reproducible configuration for a small Ubuntu development server. The repository manages a deliberate set of host settings. It does not try to snapshot every file on a running machine.

## Supported host

- Ubuntu Server 24.04 LTS
- x86-64
- a non-root user with sudo access
- an initial SSH access method installed before bootstrap

Ubuntu release upgrades stay outside the playbook because they require a reboot and recovery checks.

## Fresh server

The repository is public and contains no credentials, so a new host can clone it over HTTPS:

```bash
sudo apt-get update
sudo apt-get install -y git
git clone https://github.com/YannickHerrero/server-config.git ~/dev/server-config
cd ~/dev/server-config
./install.sh
```

`install.sh` installs the validation and Ansible packages from Ubuntu, validates the checkout, asks sudo for authorization, and applies the local playbook.

On a new host, the first application installs Tailscale and stops before changing SSH or UFW. Authenticate the node, then apply again:

```bash
sudo tailscale up --hostname="$(hostname)" --operator="$(id -un)" --ssh=false
./install.sh
```

The second application verifies the Tailscale address before it restricts incoming traffic. Open the managed Zsh login shell when it finishes:

```bash
exec /usr/bin/zsh -l
herdr
```

Run the interactive onboarding for the remaining human steps:

```bash
./bin/onboard
```

The TUI checks Tailscale, GitHub, Vercel, Pi, Git identity, and Ansible convergence. Select a step and press Enter. It temporarily restores the terminal before launching each official CLI, so device codes, browser URLs, sudo, and Pi `/login` work normally. The TUI never reads or stores authentication tokens.

The equivalent manual commands remain available if the TUI cannot start:

```bash
gh auth login --git-protocol https
vercel login
pi                         # then run /login
./bin/converge
```

Pi stores credentials in `~/.pi/agent/auth.json`; that file must never enter this repository.

No tracked configuration forces a dark or light palette. Herdr uses the terminal palette, Neovim keeps its default terminal-aware colors, Pi detects the terminal background, and the prompt uses transparent backgrounds.

## Daily commands

```bash
./bin/onboard              # Interactive checklist for human setup
./bin/converge             # Check, approve, apply, prove changed=0, and diagnose
./bin/validate             # Static validation, no host changes
./bin/check                # Dry run with a diff
./bin/apply                # Validate and apply once
./bin/doctor               # Read-only system report
server-config-window status # Inspect an active maintenance window
```

`converge` asks for sudo once, shows the dry-run diff, waits for explicit approval, applies twice, and fails unless the second application reports `changed=0 failed=0`. Its latest logs are stored with private permissions in `~/.local/state/server-config/logs`.

## Remote Mosh sessions

Install Tailscale and a Mosh-capable terminal on the phone or tablet, then connect the device to the same tailnet. With MagicDNS enabled, use the short hostname:

```bash
mosh yannick@normandy
```

The Tailscale IPv4 address also works. Replace the example address rather than typing it literally:

```bash
mosh yannick@100.x.y.z
```

Mosh authenticates through the existing private SSH service, then uses UDP ports `60000:61000` on `tailscale0`. UFW does not expose those ports on the server's public network interface.

## Maintenance windows

A maintenance window lets the agent converge several committed `server-config` changes after one interactive authorization. Open one for 30 minutes:

```bash
sudo server-config-window open --minutes 30
```

The maximum duration is eight hours (`--minutes 480`). Opening a window keeps the Citadel dashboard available but suspends its other running Supervisor services, including Normandy. The broker records the exact running set and restores it when the window closes or expires.

While the window is open, the agent uses:

```bash
server-config-window status
server-config-window converge
server-config-window close
```

`converge` accepts no Ansible arguments. It requires a clean committed `main` that is not behind `origin/main`, then runs validation, an Ansible dry run, the apply, a second dry run that must report `changed=0`, and doctor. It writes private audit and command logs under `/var/log/server-config`. A failed convergence returns an error but leaves the window open until its original deadline or an explicit close. It never commits or pushes source changes.

Citadel displays the remaining time and exposes a fixed close action. Service controls and maintenance actions stay locked while the window is active. Citadel cannot request convergence through its API.

A normal window skips access, firewall, SSH, Tailscale, sudo, user-account, Citadel, and maintenance-window tasks. To authorize the host-access categories for the whole window, open it with an additional warning:

```bash
sudo server-config-window open --minutes 30 --allow-sensitive
```

Citadel bootstrap and maintenance-window tasks always remain blocked because they control the dashboard and the broker itself. Apply changes to those tasks through the ordinary interactive workflow.

The broker grants root-equivalent execution of the committed playbook during the authorized period. Its systemd service and executable remain root-owned, it installs no passwordless sudo rule, and only the managed Unix user can access its runtime socket. The dashboard remains available because the broker suspends the services that could expose the socket through a remote shell. Do not open a window while another person or untrusted process can use the managed Unix account.

Git identity is optional local metadata. The onboarding form writes it to the ignored file `config/git/identity.local` with mode `0600`. The playbook links it into the effective global Git configuration while preserving authentication managed by `gh`. `config/git/identity.example` documents the file format.

To inspect a remote host from a trusted control machine, create the ignored file `inventory/remote.local.yml` and pass it explicitly:

```bash
./bin/check -i inventory/remote.local.yml
```

## Managed in version 1

- a small package set for administration and diagnostics
- shared libraries and fonts for project-scoped Playwright Chromium headless tests
- pinned rootless Docker Engine, Compose, and Buildx without a rootful socket
- a path-bound AppArmor user-namespace profile for the pinned rootlesskit binary
- a private Multica self-host stack on Tailscale HTTPS port `8444`
- an isolated `multica` account with dedicated Pi, GitHub, Docker, and project state
- twice-daily Multica project synchronization in `Europe/Paris`
- pinned Java and Android SDK tools with a KVM-backed headless API 35 AVD
- daily Ubuntu security updates without automatic reboot
- an 8 GiB swap file
- weekly SSD TRIM
- UTC system time
- pinned mise, Node.js, Bun, pnpm, Rust, Pi, Herdr, gh, Vercel, Neovim, LSP, formatter, and terminal CLI versions
- Tailscale installation with interactive authentication
- UFW with public traffic denied and SSH allowed only through Tailscale
- Mosh sessions through Tailscale only
- password-based OpenSSH for the managed user, with root login disabled
- portable Zsh configuration with pinned plugins and a transparent prompt
- optional local Git identity without publishing personal metadata
- a pinned Ratatui onboarding TUI for interactive authentication and setup
- tracked global `AGENTS.md`, portable Pi skills, and stable Pi settings merged without touching authentication
- tracked Herdr configuration with `Ctrl+A`, `|` vertical split, and `-` horizontal split
- tracked Neovim configuration and plugin lockfile without tmux integration or a forced color theme
- the Supervisor package and Citadel controller bootstrap
- bounded server-config maintenance windows with an eight-hour maximum
- removal of the unused `bind9` server
- read-only checks for the OS, RAID, storage, private access, network, KVM, shell, user tools, Pi, Herdr, and Citadel

The playbook does not remove packages that were installed manually.

Browser tests use the Chromium headless shell pinned by each project's Playwright dependency. The server configuration supplies its shared libraries and basic web fonts, but does not install a system browser, desktop environment, display server, GTK, or Xvfb.

The playbook installs Supervisor, disables its distribution-wide daemon, and starts the private Citadel controller. Citadel owns application definitions, lifecycle, logs, health checks, and Tailscale Serve routes. Application repositories and Citadel runtime data remain outside `server-config`.

Multica's server checkout and private environment live outside this repository. The tracked configuration pins its CLI, source commit, images, reverse proxy, daemon, Android runtime, agent instructions, helper commands, and timers. Follow [`docs/multica.md`](docs/multica.md) for the interactive logins and first activation.

## Not managed yet

- Ubuntu release upgrades
- tailnet policy, Tailscale authentication, key expiry, or passwordless sudo policy
- Maestro or a system browser
- application repositories, user data, torrents, or off-host backups
- Multica, Pi, GitHub, Tailscale, or Android emulator sessions and credentials
- tailnet policy and Citadel route activation
- Vercel authentication

Add these only after the server needs them.

## Version updates

Downloaded bootstrap tools use versions and checksums declared in `group_vars/all.yml`. User runtimes and CLIs use exact versions in `config/mise/config.toml`. Update these files through a reviewed commit, then run `./bin/check` and `./bin/apply`. Do not run `mise use -g`, `pi update`, or global npm installs directly on the host.

## Secrets

Keep secrets outside Git. The ignore rules cover local inventories, Git identity, `.env` files, `auth.json`, and a local `secrets/` directory, but ignore rules are not a substitute for reviewing every staged file before a commit.
