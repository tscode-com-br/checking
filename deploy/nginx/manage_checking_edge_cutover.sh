#!/usr/bin/env bash

set -euo pipefail

mode=""
server_config=""
routes_file="deploy/nginx/checking-edge-routes.conf"
backup_file=""
http_config_target=""
http_rules_file="deploy/nginx/checking-edge-http.conf"
http_backup_file=""
reload_nginx="false"

begin_marker="# BEGIN CHECKCHECK EDGE ROUTES"
end_marker="# END CHECKCHECK EDGE ROUTES"

usage() {
  cat <<'EOF'
Usage:
  bash deploy/nginx/manage_checking_edge_cutover.sh apply --server-config <path> [--routes-file <path>] [--http-config-target <path>] [--http-rules-file <path>] [--reload]
  bash deploy/nginx/manage_checking_edge_cutover.sh rollback --server-config <path> --backup-file <path> [--http-config-target <path>] [--http-backup-file <path>] [--reload]

Options:
  --server-config <path>  Path to the public HTTPS server config file on the droplet.
  --routes-file <path>    Proxy routes template. Default: deploy/nginx/checking-edge-routes.conf.
  --http-config-target <path>
                          Optional nginx http{} include target for global rate-limit zones.
                          Example: /etc/nginx/conf.d/checkcheck-edge-http.conf.
  --http-rules-file <path>
                          Source file for the optional http{} include. Default: deploy/nginx/checking-edge-http.conf.
  --backup-file <path>    Backup file used for rollback.
  --http-backup-file <path>
                          Backup file used for rollback of the optional http{} include.
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

restore_apply_backups() {
  if [ -n "$backup_file" ] && [ -f "$backup_file" ]; then
    cp "$backup_file" "$server_config" || true
  fi

  if [ -n "$http_config_target" ]; then
    if [ -n "$http_backup_file" ] && [ -f "$http_backup_file" ]; then
      cp "$http_backup_file" "$http_config_target" || true
    else
      rm -f "$http_config_target" || true
    fi
  fi
}

replace_managed_block() {
  local source_file="$1"
  local target_file="$2"
  local temp_file
  local merged_file

  temp_file="$(mktemp)"
  merged_file="$(mktemp)"
  awk -v begin="$begin_marker" -v end="$end_marker" '
    $0 == begin { in_block = 1; next }
    $0 == end { in_block = 0; next }
    in_block == 0 { print }
  ' "$target_file" > "$temp_file"

  if ! awk -v begin="$begin_marker" -v end="$end_marker" -v source="$source_file" '
    function emit_block() {
      print ""
      print begin
      while ((getline line < source) > 0) {
        print line
      }
      close(source)
      print end
    }

    BEGIN {
      in_server = 0
      depth = 0
      inserted = 0
    }

    {
      line = $0
      opens_line = line
      closes_line = line
      opens = gsub(/\{/, "{", opens_line)
      closes = gsub(/\}/, "}", closes_line)

      if (!in_server && line ~ /^[[:space:]]*server[[:space:]]*\{[[:space:]]*$/) {
        in_server = 1
      }

      if (in_server && !inserted && closes > 0 && depth + opens - closes == 0) {
        emit_block()
        inserted = 1
      }

      print line

      if (in_server) {
        depth += opens - closes
      }
    }

    END {
      if (!inserted) {
        exit 2
      }
    }
  ' "$temp_file" > "$merged_file"; then
    rm -f "$temp_file" "$merged_file"
    fail "Unable to place the managed proxy block inside a server {} block in $target_file"
  fi

  mv "$merged_file" "$target_file"

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
    --http-config-target)
      http_config_target="$2"
      shift 2
      ;;
    --http-rules-file)
      http_rules_file="$2"
      shift 2
      ;;
    --http-backup-file)
      http_backup_file="$2"
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
    if [ -n "$http_config_target" ]; then
      [ -f "$http_rules_file" ] || fail "HTTP rules file not found: $http_rules_file"
    fi

    trap 'restore_apply_backups' ERR

    backup_file="${backup_file:-/tmp/nginx-$(basename "$server_config").bak.$(date +%Y%m%d%H%M%S)}"
    cp "$server_config" "$backup_file"

    if [ -n "$http_config_target" ]; then
      mkdir -p "$(dirname "$http_config_target")"
      if [ -f "$http_config_target" ]; then
        http_backup_file="${http_backup_file:-${http_config_target}.bak.$(date +%Y%m%d%H%M%S)}"
        cp "$http_config_target" "$http_backup_file"
      fi
      cp "$http_rules_file" "$http_config_target"
    fi

    replace_managed_block "$routes_file" "$server_config"
    nginx -t >/dev/null
    trap - ERR
    pass "Backup created at $backup_file"
    if [ -n "$http_backup_file" ]; then
      pass "HTTP config backup created at $http_backup_file"
    elif [ -n "$http_config_target" ]; then
      pass "HTTP config installed at $http_config_target"
    fi
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
    if [ -n "$http_backup_file" ] && [ -z "$http_config_target" ]; then
      fail "--http-config-target is required when --http-backup-file is provided"
    fi
    cp "$backup_file" "$server_config"
    if [ -n "$http_backup_file" ]; then
      [ -f "$http_backup_file" ] || fail "HTTP backup file not found: $http_backup_file"
      cp "$http_backup_file" "$http_config_target"
    elif [ -n "$http_config_target" ]; then
      rm -f "$http_config_target"
    fi
    nginx -t >/dev/null
    pass "Backup restored from $backup_file"
    if [ -n "$http_backup_file" ]; then
      pass "HTTP config restored from $http_backup_file"
    elif [ -n "$http_config_target" ]; then
      pass "HTTP config removed from $http_config_target"
    fi
    if [ "$reload_nginx" = "true" ]; then
      systemctl reload nginx
      pass "nginx reloaded"
    fi
    ;;
esac