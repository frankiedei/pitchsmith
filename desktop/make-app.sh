#!/usr/bin/env bash
# Build Pitchsmith.app — a double-clickable macOS app that runs Pitchsmith with
# no terminal. Re-run any time; it rebuilds the bundle in place. Pass --install
# to also copy it into /Applications.
set -euo pipefail
cd "$(dirname "$0")"                       # desktop/
REPO="$(cd .. && pwd)"                      # the pitchsmith project root
HERE="$(pwd)"
APP="$REPO/Pitchsmith.app"
PY="${PYTHON:-python3}"

say() { printf "\033[1;36m▶ %s\033[0m\n" "$1"; }

say "Building the icon…"
"$PY" - <<'CHECK' || { echo "Pillow is needed: pip3 install --user Pillow"; exit 1; }
import PIL  # noqa
CHECK
"$PY" make-icon.py pitchsmith-logo.png "$HERE/AppIcon.icns"

say "Assembling $APP…"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

# launcher: inject the absolute repo path so the app works from /Applications
sed "s|__REPO__|$REPO|g" launcher.sh > "$APP/Contents/MacOS/Pitchsmith"
chmod +x "$APP/Contents/MacOS/Pitchsmith"
cp AppIcon.icns "$APP/Contents/Resources/AppIcon.icns"

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
rm -f "$HERE/AppIcon.icns"

say "Done: $APP"

if [ "${1:-}" = "--install" ]; then
  say "Installing to /Applications…"
  rm -rf "/Applications/Pitchsmith.app"
  cp -R "$APP" "/Applications/Pitchsmith.app"
  say "Installed. Open it from Applications or Spotlight (⌘-Space → Pitchsmith)."
fi
