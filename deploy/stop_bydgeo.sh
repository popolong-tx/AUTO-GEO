#!/usr/bin/env bash
set -euo pipefail

BACKEND_PID_FILE="/tmp/bydgeo-backend.pid"
FRONTEND_PID_FILE="/tmp/bydgeo-frontend.pid"

kill_pidfile() {
  local pidfile="$1"
  if [ -f "$pidfile" ]; then
    pid="$(cat "$pidfile" 2>/dev/null || true)"
    if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" || true
      sleep 2
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$pidfile"
  fi
}

echo "Stopping BYDGEO..."
kill_pidfile "$BACKEND_PID_FILE"
kill_pidfile "$FRONTEND_PID_FILE"

# Fallback: kill any lingering uvicorn/vite started for BYDGEO ports
for port in 8000 5173; do
  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  for pid in $pids; do
    kill "$pid" 2>/dev/null || true
  done
done

echo "BYDGEO stopped"
