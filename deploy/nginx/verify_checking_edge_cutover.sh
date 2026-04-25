#!/usr/bin/env bash

set -euo pipefail

mode="full"
public_base_url="https://tscode.com.br"
run_nginx_test="false"

api_local_url="http://127.0.0.1:18080/api/health"
admin_local_url="http://127.0.0.1:18081/"
user_local_url="http://127.0.0.1:18082/"
transport_local_url="http://127.0.0.1:18083/"

usage() {
  cat <<'EOF'
Usage: bash deploy/nginx/verify_checking_edge_cutover.sh [options]

Options:
  --mode <local|public|full>   Validation scope. Default: full.
  --public-base-url <url>      Public base URL. Default: https://tscode.com.br.
  --nginx-test                 Run nginx -t before URL checks.
  --api-local-url <url>        Override local API health URL.
  --admin-local-url <url>      Override local admin URL.
  --user-local-url <url>       Override local user URL.
  --transport-local-url <url>  Override local transport URL.
  --help                       Show this message.
EOF
}

fail() {
  echo "[fail] $1" >&2
  exit 1
}

pass() {
  echo "[ok] $1"
}

check_contains() {
  local label="$1"
  local url="$2"
  local expected_text="$3"
  local response

  response="$(curl -fsS --max-time 20 "$url")" || fail "$label indisponivel em $url"
  printf '%s' "$response" | grep -F "$expected_text" >/dev/null || fail "$label respondeu sem o texto esperado: $expected_text"
  pass "$label"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --mode)
      mode="$2"
      shift 2
      ;;
    --public-base-url)
      public_base_url="$2"
      shift 2
      ;;
    --nginx-test)
      run_nginx_test="true"
      shift 1
      ;;
    --api-local-url)
      api_local_url="$2"
      shift 2
      ;;
    --admin-local-url)
      admin_local_url="$2"
      shift 2
      ;;
    --user-local-url)
      user_local_url="$2"
      shift 2
      ;;
    --transport-local-url)
      transport_local_url="$2"
      shift 2
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      fail "Argumento desconhecido: $1"
      ;;
  esac
done

case "$mode" in
  local|public|full)
    ;;
  *)
    fail "Modo invalido: $mode"
    ;;
esac

if [ "$run_nginx_test" = "true" ]; then
  nginx -t >/dev/null
  pass "nginx -t"
fi

if [ "$mode" = "local" ] || [ "$mode" = "full" ]; then
  check_contains "Local API" "$api_local_url" '"status":"ok"'
  check_contains "Local admin-web" "$admin_local_url" "Checking Admin"
  check_contains "Local user-web" "$user_local_url" 'id="checkForm"'
  check_contains "Local transport-web" "$transport_local_url" "Checking Transport"
fi

if [ "$mode" = "public" ] || [ "$mode" = "full" ]; then
  check_contains "Public API" "$public_base_url/api/health" '"status":"ok"'
  check_contains "Public admin" "$public_base_url/checking/admin" "Checking Admin"
  check_contains "Public user" "$public_base_url/checking/user" 'id="checkForm"'
  check_contains "Public transport" "$public_base_url/checking/transport" "Checking Transport"
fi

pass "Proxy cutover verification concluida"