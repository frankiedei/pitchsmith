#!/bin/bash
# Pitchsmith.app launcher - starts the backend, opens the UI as a localhost tab
# in your default browser, and stops the backend when you quit the app. No
# terminal required. __REPO__ is filled in by make-app.sh at build time.
REPO="__REPO__"
PORT=8790
URL="http://127.0.0.1:${PORT}"
LOG="$HOME/Library/Logs/Pitchsmith.log"

note() { osascript -e "display notification \"$1\" with title \"Pitchsmith\"" >/dev/null 2>&1; }
fail() {
  osascript -e "display dialog \"$1\" with title \"Pitchsmith\" buttons {\"OK\"} default button \"OK\" with icon stop" >/dev/null 2>&1
  exit 1
}

# open the localhost URL as a normal tab in the default browser (no separate
# chromeless app window)
open_window() { open "$URL"; }

# already up (e.g. started elsewhere)? just open the window and finish.
if curl -s -m 2 "$URL/api/v1/health" >/dev/null 2>&1; then
  open_window
  exit 0
fi

[ -d "$REPO" ] || fail "Can't find the Pitchsmith project folder at:\n$REPO\n\nIf you moved it, rebuild the app with desktop/make-app.sh."
cd "$REPO" || fail "Could not open $REPO"

# first-run setup (skipped once installed): venv, deps, built UI
if [ ! -d backend/.venv ] || [ ! -d frontend/dist ]; then
  note "First run: setting things up, this takes a minute..."
fi
if [ ! -d backend/.venv ]; then
  command -v python3 >/dev/null 2>&1 || fail "Python 3 is required but was not found. Install it from python.org, then reopen Pitchsmith."
  python3 -m venv backend/.venv || fail "Could not create the Python environment."
  backend/.venv/bin/pip install -q --upgrade pip
  backend/.venv/bin/pip install -q -r backend/requirements.txt || fail "Could not install backend dependencies."
fi
[ -f backend/.env ] || cp backend/.env.example backend/.env
if [ ! -d frontend/dist ]; then
  command -v npm >/dev/null 2>&1 || fail "Node.js (npm) is required for first-time setup. Install it from nodejs.org, then reopen Pitchsmith."
  ( cd frontend && npm install --silent && npm run build --silent ) || fail "Could not build the interface."
fi

# API key: ask once (or again if left blank), store it in ~/Library, and export
# it so the backend picks it up. Empty is fine - the app still runs, it just
# can't generate drafts until a key is added.
KEYFILE="$HOME/Library/Application Support/Pitchsmith/apikey"
mkdir -p "$(dirname "$KEYFILE")"
if [ ! -s "$KEYFILE" ]; then
  KEY=$(osascript <<'OSA' 2>/dev/null
try
  set r to display dialog "Welcome to Pitchsmith." & return & return & "Paste your Anthropic API key to enable pitch generation (get one at console.anthropic.com)." & return & return & "You can leave this blank and add it later." default answer "" with title "Pitchsmith" buttons {"Continue"} default button "Continue"
  return text returned of r
end try
OSA
)
  printf '%s' "$KEY" > "$KEYFILE"
fi
export ANTHROPIC_API_KEY="$(cat "$KEYFILE" 2>/dev/null)"

# start the backend (module path resolves from backend/)
note "Starting Pitchsmith..."
( cd "$REPO/backend" && exec "$REPO/backend/.venv/bin/python" -m app.main ) >"$LOG" 2>&1 &
BACK=$!

# quit -> stop the backend
cleanup() { kill "$BACK" 2>/dev/null; wait "$BACK" 2>/dev/null; exit 0; }
trap cleanup TERM INT

# wait for health, then open the window
for _ in $(seq 1 60); do
  curl -s -m 1 "$URL/api/v1/health" >/dev/null 2>&1 && break
  # if the backend died during startup, surface the log tail
  kill -0 "$BACK" 2>/dev/null || fail "Pitchsmith failed to start. Details in:\n$LOG"
  sleep 0.5
done
curl -s -m 1 "$URL/api/v1/health" >/dev/null 2>&1 || fail "Pitchsmith did not respond in time. Details in:\n$LOG"

open_window

# stay resident so the Dock shows Pitchsmith running; quitting triggers cleanup
wait "$BACK"
