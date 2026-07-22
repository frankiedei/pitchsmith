#!/bin/bash
# Self-contained Pitchsmith.app launcher. Everything it needs (Python, deps,
# built UI) lives inside the bundle; user data lives in ~/Library. No system
# Python, Node, or terminal required.
BUNDLE="$(cd "$(dirname "$0")/../.." && pwd)"     # …/Pitchsmith.app
RES="$BUNDLE/Contents/Resources"
APP="$RES/app"
PY="$RES/python/bin/python3"
PORT=8790
URL="http://127.0.0.1:${PORT}"
DATA="$HOME/Library/Application Support/Pitchsmith"
KEYFILE="$DATA/apikey"
LOG="$HOME/Library/Logs/Pitchsmith.log"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
EDGE="/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"

note() { osascript -e "display notification \"$1\" with title \"Pitchsmith\"" >/dev/null 2>&1; }
fail() {
  osascript -e "display dialog \"$1\" with title \"Pitchsmith\" buttons {\"OK\"} default button \"OK\" with icon stop" >/dev/null 2>&1
  exit 1
}
open_window() {
  if [ -x "$CHROME" ]; then "$CHROME" --app="$URL" >/dev/null 2>&1 &
  elif [ -x "$EDGE" ]; then "$EDGE" --app="$URL" >/dev/null 2>&1 &
  else open "$URL"; fi
}

mkdir -p "$DATA"

# already running (e.g. reopened)? just show the window.
if curl -s -m 2 "$URL/api/v1/health" >/dev/null 2>&1; then
  open_window; exit 0
fi

# first run (or left blank last time): ask for the API key, store it in ~/Library
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

export PORT="$PORT"                       # the backend binds this (config reads $PORT)
export PITCHSMITH_DATA_DIR="$DATA"
export DATABASE_URL="sqlite:////${DATA}/pitchsmith.db"
export ANTHROPIC_API_KEY="$(cat "$KEYFILE" 2>/dev/null)"

note "Starting Pitchsmith…"
( cd "$APP/backend" && exec "$PY" -m app.main ) >"$LOG" 2>&1 &
BACK=$!

cleanup() { kill "$BACK" 2>/dev/null; wait "$BACK" 2>/dev/null; exit 0; }
trap cleanup TERM INT

for _ in $(seq 1 60); do
  curl -s -m 1 "$URL/api/v1/health" >/dev/null 2>&1 && break
  kill -0 "$BACK" 2>/dev/null || fail "Pitchsmith failed to start. Details in:\n$LOG"
  sleep 0.5
done
curl -s -m 1 "$URL/api/v1/health" >/dev/null 2>&1 || fail "Pitchsmith did not respond in time. Details in:\n$LOG"

open_window
wait "$BACK"
