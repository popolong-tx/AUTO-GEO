#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="${ROOT_DIR}"
BACKEND_DIR="${APP_DIR}/backend"
FRONTEND_DIR="${APP_DIR}/frontend"
BACKEND_LOG="/tmp/bydgeo-backend.log"
FRONTEND_LOG="/tmp/bydgeo-frontend.log"
BACKEND_PID_FILE="/tmp/bydgeo-backend.pid"
FRONTEND_PID_FILE="/tmp/bydgeo-frontend.pid"

start_backend() {
  cd "$BACKEND_DIR"
  if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv >/dev/null 2>&1 || true
    if [ ! -x .venv/bin/python ] && [ -x /usr/bin/python3 ]; then
      /usr/bin/python3 -m venv .venv >/dev/null 2>&1 || true
    fi
  fi
  if [ -f .env ]; then
    set -a
    source .env
    set +a
  fi
  if [ ! -x .venv/bin/python ]; then
    echo "Python venv is missing ensurepip support; please install python3-venv or create .venv manually."
    exit 1
  fi
  nohup .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir "$BACKEND_DIR" > "$BACKEND_LOG" 2>&1 &
  echo $! > "$BACKEND_PID_FILE"
}

start_frontend() {
  cd "$FRONTEND_DIR"
  nohup npm run dev -- --host 0.0.0.0 --port 5173 > "$FRONTEND_LOG" 2>&1 &
  echo $! > "$FRONTEND_PID_FILE"
}

wait_ready() {
  for _ in $(seq 1 30); do
    if curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1 && curl -sf http://127.0.0.1:5173/ >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

echo "Starting BYDGEO..."
start_backend
start_frontend
if wait_ready; then
  echo "BYDGEO started"
  echo "Backend: http://0.0.0.0:8000"
  echo "Frontend: http://0.0.0.0:5173"
else
  echo "Failed to start BYDGEO"
  echo "Backend log: $BACKEND_LOG"
  echo "Frontend log: $FRONTEND_LOG"
  exit 1
fi
