#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

fail() {
    printf 'error: %s\n' "$*" >&2
    exit 1
}

[[ $(uname -s) == Linux ]] || fail "server-config installs only on Ubuntu 24.04 x86-64"
[[ -r /etc/os-release ]] || fail "cannot read /etc/os-release"
# shellcheck source=/dev/null
. /etc/os-release

[[ ${ID:-} == ubuntu ]] || fail "unsupported distribution: ${ID:-unknown}"
[[ ${VERSION_ID:-} == 24.04 ]] || fail "unsupported Ubuntu release: ${VERSION_ID:-unknown}; upgrade to 24.04 first"
[[ $(uname -m) == x86_64 ]] || fail "unsupported architecture: $(uname -m)"
[[ ${EUID} -ne 0 ]] || fail "run this script as the target user, not root"

printf 'Installing the local provisioning tools from Ubuntu...\n'
sudo -v
sudo apt-get update
sudo apt-get install -y ansible-core ansible-lint shellcheck yamllint

exec "$ROOT_DIR/bin/apply"
