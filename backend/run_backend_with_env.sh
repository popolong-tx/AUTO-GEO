#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
set -a
source ./.env
set +a
PID_FILE=".backend.pid"
if [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
elif [ -x ".venv/bin/python3" ]; then
  PYTHON_BIN=".venv/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
else
  echo "No python interpreter found"
  exit 1
fi
"$PYTHON_BIN" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
pid=$!
echo "$pid" > "$PID_FILE"
echo "Backend started with PID $pid"
wait "$pid"
