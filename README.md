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

Start Pi inside a Herdr pane:

```bash
pi
```

Inside Pi, run `/login` and select a provider. Pi stores credentials in `~/.pi/agent/auth.json`; that file must never enter this repository.

Authenticate the user-scoped deployment CLIs separately:

```bash
gh auth login --git-protocol https
vercel login
```

No tracked configuration forces a dark or light palette. Herdr uses the terminal palette, Neovim keeps its default terminal-aware colors, Pi detects the terminal background, and the prompt uses transparent backgrounds.

## Daily commands

```bash
./bin/validate             # Static validation, no host changes
./bin/check                # Dry run with a diff
./bin/apply                # Validate and apply
./bin/doctor               # Read-only system report
```

To inspect a remote host from a trusted control machine, create the ignored file `inventory/remote.local.yml` and pass it explicitly:

```bash
./bin/check -i inventory/remote.local.yml
```

## Managed in version 1

- a small package set for administration and diagnostics
- daily Ubuntu security updates without automatic reboot
- an 8 GiB swap file
- weekly SSD TRIM
- UTC system time
- pinned mise, Node.js, Bun, pnpm, Rust, Pi, Herdr, gh, Vercel, Neovim, LSP, formatter, and terminal CLI versions
- Tailscale installation with interactive authentication
- UFW with public traffic denied and SSH allowed only through Tailscale
- password-based OpenSSH for the managed user, with root login disabled
- portable Zsh configuration with pinned plugins and a transparent prompt
- tracked global `AGENTS.md` and stable Pi settings merged without touching authentication
- tracked Herdr configuration with `Ctrl+A`, `|` vertical split, and `-` horizontal split
- tracked Neovim configuration and plugin lockfile without tmux integration or a forced color theme
- removal of the unused `bind9` server
- read-only checks for the OS, RAID, storage, private access, network, KVM, shell, user tools, Pi, and Herdr

The playbook does not remove packages that were installed manually.

## Not managed yet

- Ubuntu release upgrades
- tailnet policy, Tailscale authentication, key expiry, or sudo policy
- Android SDK, emulator, Java, browsers, or Maestro
- Docker
- Git identity
- application services, repositories, user data, torrents, or backups
- Pi authentication, mutable state, sessions, extensions, skills, prompts, packages, or themes
- gh and Vercel authentication

Add these only after the server needs them.

## Version updates

Downloaded bootstrap tools use versions and checksums declared in `group_vars/all.yml`. User runtimes and CLIs use exact versions in `config/mise/config.toml`. Update these files through a reviewed commit, then run `./bin/check` and `./bin/apply`. Do not run `mise use -g`, `pi update`, or global npm installs directly on the host.

## Secrets

Keep secrets outside Git. The ignore rules cover local inventories, `.env` files, `auth.json`, and a local `secrets/` directory, but ignore rules are not a substitute for reviewing every staged file before a commit.
