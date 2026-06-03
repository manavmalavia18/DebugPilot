#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

API_PORT="${API_PORT:-8000}"
UI_PORT="${UI_PORT:-5173}"
API_PID=""
UI_PID=""

cleanup() {
  echo ""
  echo "Shutting down..."
  [[ -n "$API_PID" ]] && kill "$API_PID" 2>/dev/null || true
  [[ -n "$UI_PID" ]] && kill "$UI_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

port_in_use() {
  lsof -ti ":$1" >/dev/null 2>&1
}

free_port() {
  local port="$1"
  local pids
  if port_in_use "$port"; then
    pids="$(lsof -ti ":$port" 2>/dev/null || true)"
    if [[ -n "$pids" ]]; then
      echo "Port $port in use — stopping previous process..."
      # shellcheck disable=SC2086
      kill $pids 2>/dev/null || true
      sleep 0.5
    fi
  fi
}

echo "DebugPilot — local dev"
echo ""

if [[ ! -f .env ]]; then
  echo "Missing .env — copy .env.example and set ANTHROPIC_API_KEY"
  exit 1
fi

free_port "$API_PORT"
free_port "$UI_PORT"

if port_in_use "$API_PORT"; then
  echo "Port $API_PORT is still in use. Stop it manually or set API_PORT."
  exit 1
fi

if port_in_use "$UI_PORT"; then
  echo "Port $UI_PORT is still in use. Stop it manually or set UI_PORT."
  exit 1
fi

if [[ ! -d .venv ]]; then
  echo "Creating Python venv..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "Installing Python dependencies..."
pip install -q -r requirements.txt

echo "Installing frontend dependencies..."
(cd frontend && npm install --silent)

echo ""
echo "Starting API on http://127.0.0.1:${API_PORT}"
uvicorn app.main:app --host 127.0.0.1 --port "$API_PORT" --reload &
API_PID=$!

for _ in $(seq 1 20); do
  if curl -sf "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done

echo "Starting UI on http://127.0.0.1:${UI_PORT}"
(cd frontend && VITE_API_URL="http://127.0.0.1:${API_PORT}" npm run dev -- --host 127.0.0.1 --port "$UI_PORT") &
UI_PID=$!

echo ""
echo "Ready:"
echo "  UI:  http://127.0.0.1:${UI_PORT}"
echo "  API: http://127.0.0.1:${API_PORT}"
echo "  Docs: http://127.0.0.1:${API_PORT}/docs"
echo ""
echo "Press Ctrl+C to stop."

wait "$UI_PID"
