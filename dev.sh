#!/usr/bin/env bash
# -- Pitchsmith - run everything -----------------------------------------------
# Starts the backend (127.0.0.1:8790) and the Vite dev server (localhost:5174)
# together. Ctrl-C stops both. Bootstraps deps on first run.
# Kept deliberately close to the Label OS dev.sh so the two feel identical.
set -euo pipefail
cd "$(dirname "$0")"

say() { printf "\033[1;36m> %s\033[0m\n" "$1"; }

# first-run bootstrap
if [ ! -d backend/.venv ]; then
  say "Creating backend venv + installing deps..."
  python3 -m venv backend/.venv
  ./backend/.venv/bin/pip install -q --upgrade pip
  ./backend/.venv/bin/pip install -q -r backend/requirements.txt
fi
if [ ! -d frontend/node_modules ]; then
  say "Installing frontend deps..."
  (cd frontend && npm install --silent)
fi
if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  printf "\033[1;33m! Created backend/.env - add ANTHROPIC_API_KEY, then re-run ./dev.sh\033[0m\n"
fi

# start backend
say "Starting backend on http://127.0.0.1:8790"
(
  cd backend
  # shellcheck disable=SC1091
  source .venv/bin/activate
  exec python -m app.main
) &
BACK=$!

cleanup() {
  say "Shutting down..."
  kill "$BACK" 2>/dev/null || true
  wait "$BACK" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

sleep 2
say "Starting frontend on http://localhost:5174  (Ctrl-C stops everything)"
cd frontend
npm run dev
