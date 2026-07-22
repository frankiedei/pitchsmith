#!/usr/bin/env bash
# Build a fully self-contained, distributable Pitchsmith.app for Apple Silicon:
# bundles a relocatable Python + all deps + the prebuilt UI + icon, so an end
# user only downloads and double-clicks (no Python, Node, pip, or terminal).
# Output: dist-app/Pitchsmith.app and dist-app/Pitchsmith-macos-arm64.zip
# Requires (on THIS build machine only): Node/npm, Pillow, internet.
set -euo pipefail
cd "$(dirname "$0")"                                   # desktop/
REPO="$(cd .. && pwd)"
OUT="$REPO/dist-app"
APP="$OUT/Pitchsmith.app"
RES="$APP/Contents/Resources"
ZIP="$OUT/Pitchsmith-macos-arm64.zip"
CACHE="$PWD/.cache"

# relocatable CPython (python-build-standalone), Apple Silicon
PYVER="3.12.13"; PBS_TAG="20260718"
PBS_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/cpython-${PYVER}%2B${PBS_TAG}-aarch64-apple-darwin-install_only.tar.gz"

say() { printf "\033[1;36m▶ %s\033[0m\n" "$1"; }

mkdir -p "$CACHE" "$OUT"

say "Building the icon…"
python3 make-icon.py pitchsmith-logo.png "$CACHE/AppIcon.icns"

say "Building the UI…"
( cd "$REPO/frontend" && npm install --silent && npm run build --silent )

if [ ! -x "$CACHE/python/bin/python3" ]; then
  say "Fetching bundled Python (one-time, cached)…"
  curl -sL -o "$CACHE/python.tar.gz" "$PBS_URL"
  rm -rf "$CACHE/python"
  tar -xzf "$CACHE/python.tar.gz" -C "$CACHE"
fi

say "Assembling $APP…"
rm -rf "$APP"
mkdir -p "$RES/app/backend" "$RES/app/frontend" "$APP/Contents/MacOS"

# bundled interpreter (fresh copy) + backend deps installed into it
rm -rf "$RES/python"
cp -R "$CACHE/python" "$RES/python"
"$RES/python/bin/python3" -m pip install -q --disable-pip-version-check \
  -r "$REPO/backend/requirements.txt"
# drop caches to slim the bundle
find "$RES/python" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true

# app code (no venv/data/env/caches) + prebuilt UI
rsync -a --exclude '.venv' --exclude 'data' --exclude '.env' \
  --exclude '__pycache__' --exclude '*.pyc' "$REPO/backend/" "$RES/app/backend/"
cp -R "$REPO/frontend/dist" "$RES/app/frontend/dist"

# launcher + icon + Info.plist
cp launcher-bundled.sh "$APP/Contents/MacOS/Pitchsmith"
chmod +x "$APP/Contents/MacOS/Pitchsmith"
cp "$CACHE/AppIcon.icns" "$RES/AppIcon.icns"
cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Pitchsmith</string>
  <key>CFBundleDisplayName</key><string>Pitchsmith</string>
  <key>CFBundleIdentifier</key><string>co.hallwood.pitchsmith</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>Pitchsmith</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST
touch "$APP"

say "Zipping (ditto, preserves the bundled symlinks)…"
rm -f "$ZIP"
( cd "$OUT" && ditto -c -k --sequesterRsrc --keepParent "Pitchsmith.app" "$ZIP" )

say "Done."
du -sh "$APP" "$ZIP" | sed 's/^/   /'
