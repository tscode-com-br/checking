#!/usr/bin/env bash
# Inject admin2-specific nginx routes into the HTTPS (listen 443) server block.
# Uses dedicated markers so it does not conflict with the main edge-routes managed block.

set -euo pipefail

server_config=""
routes_file="deploy/nginx/checking-admin2-routes.conf"
reload_nginx="false"

begin_marker="# BEGIN ADMIN2 ROUTES"
end_marker="# END ADMIN2 ROUTES"

fail() { echo "[fail] $1" >&2; exit 1; }
pass() { echo "[ok] $1"; }

while [ "$#" -gt 0 ]; do
  case "$1" in
    --server-config) server_config="$2"; shift 2 ;;
    --routes-file)   routes_file="$2";   shift 2 ;;
    --reload)        reload_nginx="true"; shift 1 ;;
    --help)
      echo "Usage: $0 --server-config <path> [--routes-file <path>] [--reload]"
      exit 0 ;;
    *) fail "Unknown argument: $1" ;;
  esac
done

[ -n "$server_config" ] || fail "--server-config is required"
[ -f "$server_config" ] || fail "Server config not found: $server_config"
[ -f "$routes_file" ]   || fail "Routes file not found: $routes_file"

backup="${server_config}.admin2.bak.$(date +%Y%m%d%H%M%S)"
cp "$server_config" "$backup"

temp="$(mktemp)"
merged="$(mktemp)"

cleanup() { rm -f "$temp" "$merged"; }
trap cleanup EXIT

# Strip existing admin2 marker block (idempotent)
awk -v begin="$begin_marker" -v end="$end_marker" '
  $0 == begin { in_block = 1; next }
  $0 == end   { in_block = 0; next }
  in_block == 0 { print }
' "$server_config" > "$temp"

# Insert admin2 routes before the closing brace of the HTTPS (listen 443) server block
if ! awk -v begin="$begin_marker" -v end="$end_marker" -v source="$routes_file" '
  BEGIN { n = 0 }
  { lines[++n] = $0 }
  END {
    in_server = 0; depth = 0; has_443 = 0; target_close = 0
    for (i = 1; i <= n; i++) {
      tmp = lines[i]; opens = gsub(/\{/, "", tmp)
      tmp = lines[i]; closes = gsub(/\}/, "", tmp)
      if (!in_server && lines[i] ~ /^[[:space:]]*server[[:space:]]*\{[[:space:]]*$/) {
        in_server = 1; depth = 0; has_443 = 0
      }
      if (in_server) {
        if (lines[i] ~ /listen[[:space:]].*443/) has_443 = 1
        if (closes > 0 && depth + opens - closes == 0) {
          if (has_443) target_close = i
          in_server = 0
        }
        depth += opens - closes
      }
    }
    if (target_close == 0) exit 2
    for (i = 1; i <= n; i++) {
      if (i == target_close) {
        print ""
        print begin
        while ((getline bline < source) > 0) print bline
        close(source)
        print end
      }
      print lines[i]
    }
  }
' "$temp" > "$merged"; then
  cp "$backup" "$server_config"
  fail "Could not insert admin2 routes into nginx HTTPS server block in $server_config"
fi

mv "$merged" "$server_config"

if ! nginx -t 2>&1; then
  cp "$backup" "$server_config"
  fail "nginx config test failed after admin2 route injection; config restored from $backup"
fi

if [ "$reload_nginx" = "true" ]; then
  systemctl reload nginx
  pass "nginx reloaded with admin2 routes"
else
  pass "admin2 routes applied (reload skipped)"
fi
