#!/bin/sh
set -e

ROOT=$(cd "$(dirname "$0")" && pwd)
PID_FILE="$ROOT/.service-pids"

log() { printf '\033[36m[kaifang-meta]\033[0m %s\n' "$*"; }

if [ ! -f "$PID_FILE" ]; then
  log "没有正在运行的平台源码进程"
  exit 0
fi

while read -r role pid; do
  case "$pid" in ''|0|1|*[!0-9]*) continue ;; esac
  command=$(ps -p "$pid" -o command= 2>/dev/null || true)
  case "$role:$command" in
    backend:*python*run.py*|worker:*app.worker*|frontend:*pnpm*dev*|frontend:*vite*)
      log "停止 $role（PID $pid）"
      kill -TERM "$pid" 2>/dev/null || true
      ;;
  esac
done < "$PID_FILE"

rm -f "$PID_FILE"
