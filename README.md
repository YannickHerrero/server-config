# server-config

Reproducible configuration for a small Ubuntu development server. The repository manages a deliberate set of host settings. It does not try to snapshot every file on a running machine.

## Supported host

- Ubuntu Server 24.04 LTS
- x86-64
- a non-root user with sudo access
- an SSH key installed before bootstrap

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

Open a new login shell when it finishes:

```bash
exec "$SHELL" -l
pi
```

Inside Pi, run `/login` and select a provider. Pi stores credentials in `~/.pi/agent/auth.json`; that file must never enter this repository.

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
- pinned Node.js and Pi versions
- read-only checks for the OS, RAID, storage, network, KVM, Node.js, and Pi

The playbook does not remove packages that were installed manually.

## Not managed yet

- Ubuntu release upgrades
- Tailscale, SSH hardening, sudo policy, or firewall rules
- Android SDK, emulator, Java, browsers, or Maestro
- application runtimes other than the Node.js version required by Pi
- Docker
- shell, editor, terminal, or Git dotfiles
- application services, repositories, user data, torrents, or backups
- Pi authentication, settings, sessions, extensions, skills, prompts, or themes

Add these only after the server needs them.

## Version updates

Downloaded tools use versions and checksums declared in `group_vars/all.yml`. Update that file through a reviewed commit, then run `./bin/check` and `./bin/apply`. Do not update Pi directly on the host.

## Secrets

Keep secrets outside Git. The ignore rules cover local inventories, `.env` files, `auth.json`, and a local `secrets/` directory, but ignore rules are not a substitute for reviewing every staged file before a commit.
