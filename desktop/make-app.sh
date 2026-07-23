#!/usr/bin/env bash
# Build Pitchsmith.app - a double-clickable macOS app that runs Pitchsmith with
# no terminal. Re-run any time; it rebuilds the bundle in place. Pass --install
# to also copy it into /Applications.
set -euo pipefail
cd "$(dirname "$0")"                       # desktop/
REPO="$(cd .. && pwd)"                      # the pitchsmith project root
HERE="$(pwd)"
APP="$REPO/Pitchsmith.app"
PY="${PYTHON:-python3}"

say() { printf "\033[1;36m> %s\033[0m\n" "$1"; }

# Use the committed icon when it's present (the common case, and the one the
# installer relies on so it needs no Pillow). Only regenerate from the PNG when
# the icon is missing AND Pillow is available.
ICON="$HERE/AppIcon.icns"
if [ ! -f "$ICON" ]; then
  if "$PY" -c "import PIL" >/dev/null 2>&1; then
    say "Building the icon..."
    "$PY" make-icon.py pitchsmith-logo.png "$ICON"
  else
    say "No AppIcon.icns and no Pillow - building the app without a custom icon."
    ICON=""
  fi
fi

say "Assembling $APP..."
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

# launcher: inject the absolute repo path so the app works from /Applications
sed "s|__REPO__|$REPO|g" launcher.sh > "$APP/Contents/MacOS/Pitchsmith"
chmod +x "$APP/Contents/MacOS/Pitchsmith"
[ -n "$ICON" ] && cp "$ICON" "$APP/Contents/Resources/AppIcon.icns"

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

# refresh Finder's icon cache so the new icon shows immediately
touch "$APP"

say "Done: $APP"

if [ "${1:-}" = "--install" ]; then
  say "Installing to /Applications..."
  rm -rf "/Applications/Pitchsmith.app"
  cp -R "$APP" "/Applications/Pitchsmith.app"
  say "Installed. Open it from Applications or Spotlight (Cmd-Space -> Pitchsmith)."
fi
