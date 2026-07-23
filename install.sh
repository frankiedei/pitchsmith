#!/usr/bin/env bash
# -- Pitchsmith - one-line installer -------------------------------------------
# Fetches Pitchsmith from source, sets it up, and builds a double-clickable
# Pitchsmith.app ON THIS MACHINE (so macOS never quarantines it), then opens it.
# Run it with:
#
#   curl -fsSL https://raw.githubusercontent.com/frankiedei/pitchsmith/main/install.sh | bash
#
# You do NOT need to install Node, npm, or (usually) Python: the UI ships
# prebuilt in the repo, and if this Mac has no suitable python3 the installer
# downloads a self-contained one just for Pitchsmith. The only requirement is
# git (macOS offers it via the Command Line Tools on first use).
#
# The app is a thin launcher that runs the git checkout in ~/pitchsmith, so
# `cd ~/pitchsmith && ./pitchsmith update` keeps every machine current.
#
# Override the checkout location with:  PITCHSMITH_DIR=/path bash install.sh
set -euo pipefail

REPO_URL="https://github.com/frankiedei/pitchsmith.git"
DIR="${PITCHSMITH_DIR:-$HOME/pitchsmith}"

# self-contained Python, used ONLY if this Mac has no suitable python3
PYVER="3.12.13"; PBS_TAG="20260718"
case "$(uname -m)" in
  arm64)  PBS_ARCH="aarch64" ;;
  x86_64) PBS_ARCH="x86_64" ;;
  *)      PBS_ARCH="aarch64" ;;
esac
PBS_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/cpython-${PYVER}%2B${PBS_TAG}-${PBS_ARCH}-apple-darwin-install_only.tar.gz"

say()  { printf "\033[1;36m> %s\033[0m\n" "$1"; }
warn() { printf "\033[1;33m! %s\033[0m\n" "$1"; }
ok()   { printf "\033[1;32mOK %s\033[0m\n" "$1"; }
die()  { printf "\033[1;31mx %s\033[0m\n" "$1" >&2; exit 1; }

# --- this installer builds a macOS app; it only makes sense on a Mac ---------
# (Linux cloud shells / CI terminals can't run a .app - run this on the actual
# Mac you want Pitchsmith on.)
if [ "$(uname -s)" != "Darwin" ]; then
  die "Pitchsmith's installer builds a macOS app and must be run on a Mac (not a Linux or cloud terminal). Open Terminal on the Mac you want to use, and run it there."
fi

# --- prerequisites: git only -------------------------------------------------
if ! command -v git >/dev/null 2>&1; then
  warn "git is required and was not found."
  echo "  macOS can install it for you - run this, accept the prompt, then re-run:"
  echo "    xcode-select --install"
  die "Install git, then run the installer again."
fi

# --- clone or update ---------------------------------------------------------
if [ -d "$DIR/.git" ]; then
  say "Updating the existing checkout at $DIR..."
  git -C "$DIR" pull --ff-only || warn "git pull skipped (local changes or diverged branch)."
elif [ -e "$DIR" ]; then
  die "$DIR exists but is not a Pitchsmith checkout. Move it aside or set PITCHSMITH_DIR."
else
  say "Cloning Pitchsmith into $DIR..."
  git clone --depth 1 "$REPO_URL" "$DIR"
fi
cd "$DIR"

# --- a Python for the backend (system if suitable, else self-contained) ------
PYBIN=""
if command -v python3 >/dev/null 2>&1 \
   && python3 -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 11) else 1)' 2>/dev/null; then
  PYBIN="$(command -v python3)"
else
  BUNDLED="$DIR/backend/.python"
  if [ ! -x "$BUNDLED/bin/python3" ]; then
    say "No suitable Python found - fetching a self-contained one just for Pitchsmith..."
    curl -fsSL -o "$DIR/backend/.python.tar.gz" "$PBS_URL"
    rm -rf "$BUNDLED"; mkdir -p "$BUNDLED"
    # the tarball unpacks to a top-level python/ dir; strip it so bin/, lib/...
    # land directly in .python/ (i.e. .python/bin/python3 exists).
    tar -xzf "$DIR/backend/.python.tar.gz" -C "$BUNDLED" --strip-components=1
    rm -f "$DIR/backend/.python.tar.gz"
  fi
  PYBIN="$BUNDLED/bin/python3"
  [ -x "$PYBIN" ] || die "Could not set up a bundled Python (expected $PYBIN). Please install Python 3 from python.org and re-run."
fi

# --- backend env + deps ------------------------------------------------------
if [ ! -d backend/.venv ]; then
  say "Setting up the backend (first run installs dependencies)..."
  "$PYBIN" -m venv backend/.venv
fi
backend/.venv/bin/python -m pip install -q --upgrade pip
backend/.venv/bin/python -m pip install -q -r backend/requirements.txt
[ -f backend/.env ] || cp backend/.env.example backend/.env

# The UI ships prebuilt in the repo, so no Node/npm is needed. Guard against a
# checkout that somehow lacks it.
[ -d frontend/dist ] || die "frontend/dist is missing from the checkout - the prebuilt UI should be committed."

# --- build the double-click launcher locally (never quarantined) -------------
say "Building the Pitchsmith app..."
( cd desktop && ./make-app.sh >/dev/null )        # produces "$DIR/Pitchsmith.app"

APPS="/Applications"; [ -w "$APPS" ] || APPS="$HOME/Applications"
mkdir -p "$APPS"
rm -rf "$APPS/Pitchsmith.app"
cp -R "$DIR/Pitchsmith.app" "$APPS/Pitchsmith.app"

ok "Installed Pitchsmith.app to $APPS"
say "Opening it now..."
open "$APPS/Pitchsmith.app" 2>/dev/null || true

cat <<EOF

  Double-click Pitchsmith in $APPS (or Spotlight: Cmd-Space -> Pitchsmith) any time.
  It opens the app at http://127.0.0.1:8790 in your browser and stops when you quit.

  Update to the latest any time:   cd "$DIR" && ./pitchsmith update
  Uninstall:                       rm -rf "$DIR" "$APPS/Pitchsmith.app"

Add your Anthropic API key in the app's first-run prompt, or in $DIR/backend/.env,
to generate pitches (get one at console.anthropic.com). Without a key the app
still runs, but only the deterministic audit happens - no drafts are generated.
EOF
