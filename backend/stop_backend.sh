#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PID_FILE=".backend.pid"
if [[ ! -f "$PID_FILE" ]]; then
  echo "No PID file found: $PID_FILE"
  exit 0
fi
pid="$(cat "$PID_FILE")"
if [[ -z "$pid" ]]; then
  echo "Empty PID file"
  rm -f "$PID_FILE"
  exit 0
fi
if kill -0 "$pid" 2>/dev/null; then
  kill "$pid"
  echo "Stopped backend process $pid"
else
  echo "Process $pid not running"
fi
rm -f "$PID_FILE"
