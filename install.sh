#!/usr/bin/env bash
# ── Pitchsmith · one-line installer ───────────────────────────────────────────
# Fetches Pitchsmith fresh from source, builds it, and starts the local app.
# Run it with:
#
#   curl -fsSL https://raw.githubusercontent.com/frankiedei/pitchsmith/main/install.sh | bash
#
# It clones (or updates) the repo into ~/pitchsmith, installs everything the
# first run needs (a Python venv + node_modules, handled by the control CLI),
# builds the UI, and serves the app at http://127.0.0.1:8790. Because the install
# is a git checkout, `pitchsmith update` afterwards pulls the latest and rebuilds.
#
# Override the location with:  PITCHSMITH_DIR=/path/to/dir bash install.sh
set -euo pipefail

REPO="https://github.com/frankiedei/pitchsmith.git"
DIR="${PITCHSMITH_DIR:-$HOME/pitchsmith}"

say()  { printf "\033[1;36m▶ %s\033[0m\n" "$1"; }
warn() { printf "\033[1;33m⚠ %s\033[0m\n" "$1"; }
ok()   { printf "\033[1;32m✓ %s\033[0m\n" "$1"; }
die()  { printf "\033[1;31m✗ %s\033[0m\n" "$1" >&2; exit 1; }

# --- prerequisites -----------------------------------------------------------
missing=()
for tool in git python3 node npm; do
  command -v "$tool" >/dev/null 2>&1 || missing+=("$tool")
done
if [ "${#missing[@]}" -gt 0 ]; then
  warn "Missing: ${missing[*]}"
  echo "  Install them first. On macOS the easiest way is Homebrew (https://brew.sh):"
  echo "    brew install git python node"
  die "Cannot continue until the tools above are installed."
fi

# --- clone or update ---------------------------------------------------------
if [ -d "$DIR/.git" ]; then
  say "Found an existing checkout at $DIR — updating it…"
  cd "$DIR"
  git pull --ff-only || warn "git pull skipped (local changes or diverged branch)."
elif [ -e "$DIR" ]; then
  die "$DIR exists but is not a Pitchsmith git checkout. Move it aside or set PITCHSMITH_DIR."
else
  say "Cloning Pitchsmith into $DIR…"
  git clone --depth 1 "$REPO" "$DIR"
  cd "$DIR"
fi

# --- build + start (the control CLI bootstraps the venv, node_modules, .env) --
say "Building and starting (first run installs dependencies, this can take a minute)…"
./pitchsmith start

ok "Pitchsmith is installed at $DIR"
echo
echo "  Open it:     http://127.0.0.1:8790"
echo "  Update it:   cd \"$DIR\" && ./pitchsmith update"
echo "  Stop it:     cd \"$DIR\" && ./pitchsmith stop"
echo
echo "Add your Anthropic API key to $DIR/backend/.env to generate pitches"
echo "(get one at console.anthropic.com). Without a key the app still runs, but"
echo "the deterministic audit is all that happens — no drafts are generated."

# open the browser on macOS
command -v open >/dev/null 2>&1 && open "http://127.0.0.1:8790" 2>/dev/null || true
