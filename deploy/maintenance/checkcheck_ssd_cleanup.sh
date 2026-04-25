#!/usr/bin/env bash

set -euo pipefail

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

log "Starting Checkcheck SSD cleanup"

if command -v docker >/dev/null 2>&1; then
  log "Pruning unused Docker images"
  docker image prune -af || true

  log "Pruning unused Docker build cache"
  docker builder prune -af || true

  log "Pruning unused Docker containers, networks, and volumes"
  docker system prune -af --volumes || true

  log "Docker disk usage after cleanup"
  docker system df || true
fi

if command -v apt-get >/dev/null 2>&1; then
  log "Cleaning apt cache"
  apt-get clean || true
  rm -rf /var/lib/apt/lists/* || true
  rm -rf /var/cache/apt/archives/*.deb || true
  rm -rf /var/cache/apt/archives/partial/* || true
fi

if command -v journalctl >/dev/null 2>&1; then
  log "Vacuuming old journald logs"
  journalctl --vacuum-time=7d || true
  journalctl --vacuum-size=200M || true
fi

log "Removing stale Checkcheck temp files"
find /tmp /var/tmp -maxdepth 1 \( -name 'checkcheck-deploy-*' -o -name 'checkcheck-stage-*' -o -name 'checkcheck-rsync-*' \) -mmin +120 -exec rm -rf {} + || true

log "Root filesystem usage after cleanup"
df -h /

log "Checkcheck SSD cleanup finished"