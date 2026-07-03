#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
"$DIR/stop_bydgeo.sh" || true
sleep 2
"$DIR/start_bydgeo.sh"
