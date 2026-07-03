#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_PID_FILE="$BACKEND_DIR/.backend.pid"
FRONTEND_PID_FILE="$FRONTEND_DIR/.frontend.pid"
BACKEND_LOG="$BACKEND_DIR/backend.log"
FRONTEND_LOG="$FRONTEND_DIR/frontend.log"

usage() {
  cat <<'EOF'
Usage:
  ./run_dev.sh start   # start backend + frontend
  ./run_dev.sh stop    # stop backend + frontend
  ./run_dev.sh status  # show status
EOF
}

is_listening() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"$port" -sTCP:LISTEN -n -P >/dev/null 2>&1
  else
    return 1
  fi
}

start_backend() {
  if [[ -f "$BACKEND_PID_FILE" ]] && kill -0 "$(cat "$BACKEND_PID_FILE")" 2>/dev/null; then
    echo "[backend] already running: $(cat "$BACKEND_PID_FILE")"
    return
  fi
  mkdir -p "$BACKEND_DIR"
  (cd "$BACKEND_DIR" && ./run_backend_with_env.sh >"$BACKEND_LOG" 2>&1 & echo $! > "$BACKEND_PID_FILE")
  echo "[backend] started"
}

start_frontend() {
  if [[ -f "$FRONTEND_PID_FILE" ]] && kill -0 "$(cat "$FRONTEND_PID_FILE")" 2>/dev/null; then
    echo "[frontend] already running: $(cat "$FRONTEND_PID_FILE")"
    return
  fi
  mkdir -p "$FRONTEND_DIR"
  (cd "$FRONTEND_DIR" && npm run dev -- --host 0.0.0.0 --port 5173 >"$FRONTEND_LOG" 2>&1 & echo $! > "$FRONTEND_PID_FILE")
  echo "[frontend] started"
}

stop_pid_file() {
  local label="$1"
  local pid_file="$2"
  if [[ ! -f "$pid_file" ]]; then
    echo "[$label] no pid file"
    return
  fi
  local pid
  pid="$(cat "$pid_file")"
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid"
    echo "[$label] stopped $pid"
  else
    echo "[$label] not running"
  fi
  rm -f "$pid_file"
}

stop_backend() { stop_pid_file backend "$BACKEND_PID_FILE"; }
stop_frontend() { stop_pid_file frontend "$FRONTEND_PID_FILE"; }

status_backend() {
  if [[ -f "$BACKEND_PID_FILE" ]] && kill -0 "$(cat "$BACKEND_PID_FILE")" 2>/dev/null; then
    echo "[backend] running: $(cat "$BACKEND_PID_FILE")"
  else
    echo "[backend] stopped"
  fi
}

status_frontend() {
  if [[ -f "$FRONTEND_PID_FILE" ]] && kill -0 "$(cat "$FRONTEND_PID_FILE")" 2>/dev/null; then
    echo "[frontend] running: $(cat "$FRONTEND_PID_FILE")"
  else
    echo "[frontend] stopped"
  fi
}

case "${1:-}" in
  start)
    start_backend
    start_frontend
    echo "Backend:  http://127.0.0.1:8000"
    echo "Frontend: http://127.0.0.1:5173"
    ;;
  stop)
    stop_backend
    stop_frontend
    ;;
  status)
    status_backend
    status_frontend
    ;;
  *)
    usage
    exit 1
    ;;
esac
