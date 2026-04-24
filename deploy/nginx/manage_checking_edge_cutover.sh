#!/usr/bin/env bash

set -euo pipefail

mode=""
server_config=""
routes_file="deploy/nginx/checking-edge-routes.conf"
backup_file=""
reload_nginx="false"

begin_marker="# BEGIN CHECKCHECK EDGE ROUTES"
end_marker="# END CHECKCHECK EDGE ROUTES"

usage() {
  cat <<'EOF'
Usage:
  bash deploy/nginx/manage_checking_edge_cutover.sh apply --server-config <path> [--routes-file <path>] [--reload]
  bash deploy/nginx/manage_checking_edge_cutover.sh rollback --server-config <path> --backup-file <path> [--reload]

Options:
  --server-config <path>  Path to the public HTTPS server config file on the droplet.
  --routes-file <path>    Proxy routes template. Default: deploy/nginx/checking-edge-routes.conf.
  --backup-file <path>    Backup file used for rollback.
  --reload                Run systemctl reload nginx after a successful nginx -t.
  --help                  Show this message.
EOF
}

fail() {
  echo "[fail] $1" >&2
  exit 1
}

pass() {
  echo "[ok] $1"
}

replace_managed_block() {
  local source_file="$1"
  local target_file="$2"
  local temp_file

  temp_file="$(mktemp)"
  awk -v begin="$begin_marker" -v end="$end_marker" '
    $0 == begin { in_block = 1; next }
    $0 == end { in_block = 0; next }
    in_block == 0 { print }
  ' "$target_file" > "$temp_file"

  {
    cat "$temp_file"
    printf '\n%s\n' "$begin_marker"
    cat "$source_file"
    printf '%s\n' "$end_marker"
  } > "$target_file"

  rm -f "$temp_file"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    apply|rollback)
      if [ -n "$mode" ]; then
        fail "Mode already defined: $mode"
      fi
      mode="$1"
      shift 1
      ;;
    --server-config)
      server_config="$2"
      shift 2
      ;;
    --routes-file)
      routes_file="$2"
      shift 2
      ;;
    --backup-file)
      backup_file="$2"
      shift 2
      ;;
    --reload)
      reload_nginx="true"
      shift 1
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      fail "Unknown argument: $1"
      ;;
  esac
done

[ -n "$mode" ] || fail "Mode is required"
[ -n "$server_config" ] || fail "--server-config is required"
[ -f "$server_config" ] || fail "Server config not found: $server_config"

case "$mode" in
  apply)
    [ -f "$routes_file" ] || fail "Routes file not found: $routes_file"
    backup_file="${backup_file:-${server_config}.bak.$(date +%Y%m%d%H%M%S)}"
    cp "$server_config" "$backup_file"
    replace_managed_block "$routes_file" "$server_config"
    nginx -t >/dev/null
    pass "Backup created at $backup_file"
    pass "Managed proxy block applied to $server_config"
    if [ "$reload_nginx" = "true" ]; then
      systemctl reload nginx
      pass "nginx reloaded"
    fi
    echo "$backup_file"
    ;;
  rollback)
    [ -n "$backup_file" ] || fail "--backup-file is required for rollback"
    [ -f "$backup_file" ] || fail "Backup file not found: $backup_file"
    cp "$backup_file" "$server_config"
    nginx -t >/dev/null
    pass "Backup restored from $backup_file"
    if [ "$reload_nginx" = "true" ]; then
      systemctl reload nginx
      pass "nginx reloaded"
    fi
    ;;
esac