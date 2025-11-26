#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
API_PORT=${API_PORT:-8000}
UI_PORT=${UI_PORT:-4173}

cd "$ROOT_DIR"

echo "Starting Solace local stack (API on $API_PORT, frontend on $UI_PORT)"

echo "API and UI are for local use only. Do not expose externally."

uvicorn web.api.main:app --reload --host 0.0.0.0 --port "$API_PORT" &
API_PID=$!

cd "$ROOT_DIR/web/frontend"
npm install
npm run dev -- --host --port "$UI_PORT" &
UI_PID=$!

trap 'kill $API_PID $UI_PID' EXIT
wait
