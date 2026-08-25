#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

cat >"$TEMP_DIR/fake-sudo" <<'SH'
#!/usr/bin/env sh
set -eu
while [ "$#" -gt 0 ]; do
    case "$1" in
        -u)
            shift 2
            ;;
        -*)
            shift
            ;;
        *)
            break
            ;;
    esac
done
exec "$@"
SH
chmod 0700 "$TEMP_DIR/fake-sudo"

cd "$ROOT_DIR"
ansible-playbook --check --tags maintenance-window \
    --extra-vars server_config_maintenance_broker=true \
    --extra-vars server_config_managed_user="$(id -un)" \
    --extra-vars "ansible_become_exe=$TEMP_DIR/fake-sudo" \
    playbook.yml >"$TEMP_DIR/ansible.log"

grep -Eq \
    '^[[:alnum:]_.-]+[[:space:]]+:[[:space:]]+ok=[0-9]+[[:space:]]+changed=[0-9]+[[:space:]]+unreachable=0[[:space:]]+failed=0' \
    "$TEMP_DIR/ansible.log"
