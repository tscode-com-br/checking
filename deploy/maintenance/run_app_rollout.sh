#!/usr/bin/env bash

set -euo pipefail

phase="full"
deploy_dir=""
release_marker=".deploy-release"
release_id=""
local_health_url="http://127.0.0.1:8000/api/health"
local_health_contains='"status":"ok"'
public_health_url=""
public_health_contains='"status":"ok"'

while [ "$#" -gt 0 ]; do
  case "$1" in
    --phase)
      phase="$2"
      shift 2
      ;;
    --deploy-dir)
      deploy_dir="$2"
      shift 2
      ;;
    --release-marker)
      release_marker="$2"
      shift 2
      ;;
    --release-id)
      release_id="$2"
      shift 2
      ;;
    --local-health-url)
      local_health_url="$2"
      shift 2
      ;;
    --local-health-contains)
      local_health_contains="$2"
      shift 2
      ;;
    --public-health-url)
      public_health_url="$2"
      shift 2
      ;;
    --public-health-contains)
      public_health_contains="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1"
      exit 1
      ;;
  esac
done

if [ -z "$deploy_dir" ]; then
  echo "Missing required argument: --deploy-dir"
  exit 1
fi

case "$deploy_dir" in
  "~"|"~/"*) deploy_dir="${HOME}${deploy_dir:1}" ;;
esac

cd "$deploy_dir"

if [ ! -f .env ]; then
  echo "Arquivo .env nao encontrado em $deploy_dir"
  exit 1
fi

require_single_app_worker() {
  local app_workers
  app_workers="$({ awk -F= '$1=="APP_WORKERS" { print $2 }' .env || true; } | tail -n 1 | tr -d '[:space:]')"
  app_workers="${app_workers:-1}"

  if [ "$app_workers" != "1" ]; then
    echo "APP_WORKERS deve resolver para 1 ate a validacao real de multiworker em tests/test_multiworker_realtime_postgres.py. Valor efetivo: $app_workers"
    exit 1
  fi
}

require_single_app_worker

diagnose_failure() {
  echo "[deploy-diagnostics] phase=$phase"
  date -Is || true
  docker compose ps || true
  docker compose logs --tail=120 app || true
  if [ -n "$local_health_url" ]; then
    echo "[local-health] $local_health_url"
    curl -i "$local_health_url" || true
  fi
  if [ -n "$public_health_url" ]; then
    echo "[public-health] $public_health_url"
    curl -i "$public_health_url" || true
  fi
}

trap diagnose_failure ERR

run_migration() {
  echo "[checkpoint] migration"
  docker compose run --rm --no-deps migrate
}

start_http_runtime() {
  echo "[checkpoint] start-http"
  docker compose up -d --no-build --force-recreate --remove-orphans app forms-worker
}

validate_local_health() {
  echo "[checkpoint] validate-local-health"
  bash deploy/smoke/validate_target.sh \
    --label application \
    --compose-file docker-compose.yml \
    --service app \
    --url "$local_health_url" \
    --contains "$local_health_contains"

  echo "[checkpoint] validate-forms-worker-health"
  attempt=1
  max_attempts=15
  sleep_seconds=6
  while [ "$attempt" -le "$max_attempts" ]; do
    if docker compose exec -T forms-worker python -m sistema.app.forms_worker_healthcheck >/dev/null 2>&1; then
      echo "[validate-forms-worker-health] healthy on attempt $attempt"
      docker compose exec -T forms-worker python -m sistema.app.forms_worker_healthcheck || true
      return 0
    fi
    sleep "$sleep_seconds"
    attempt=$((attempt + 1))
  done

  echo "forms-worker healthcheck did not become healthy within $((max_attempts * sleep_seconds))s"
  docker compose ps forms-worker || true
  docker compose logs --tail=200 forms-worker || true
  exit 1
}

validate_public_health() {
  if [ -z "$public_health_url" ]; then
    echo "Public health URL is required for phase validate-public"
    exit 1
  fi

  echo "[checkpoint] validate-public-health"
  bash deploy/smoke/validate_url.sh \
    --label public-api \
    --url "$public_health_url" \
    --contains "$public_health_contains"
}

mark_release() {
  if [ -z "$release_id" ]; then
    echo "Release id is required to mark rollout success"
    exit 1
  fi

  echo "[checkpoint] mark-release"
  printf '%s\n' "$release_id" > "$release_marker"
}

case "$phase" in
  migrate)
    run_migration
    ;;
  start)
    start_http_runtime
    ;;
  validate-local)
    validate_local_health
    ;;
  validate-public)
    validate_public_health
    ;;
  mark-release)
    mark_release
    ;;
  full)
    run_migration
    start_http_runtime
    validate_local_health
    if [ -n "$public_health_url" ]; then
      validate_public_health
    fi
    mark_release
    ;;
  *)
    echo "Unknown rollout phase: $phase"
    exit 1
    ;;
esac