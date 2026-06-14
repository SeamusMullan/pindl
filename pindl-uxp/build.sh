#!/usr/bin/env bash
# Package the plugin for distribution.
#
#   ./build.sh            -> dist/pindl-uxp-<version>.zip  (load via UDT)
#
# A .ccx (the double-clickable installer QA uses) must be SIGNED. UXP's signing
# lives in the UXP Developer Tool, so the signed artifact is produced there —
# see README "Send to QA". This script builds the unsigned bundle UDT consumes
# and validates the plugin before you package.
set -euo pipefail
cd "$(dirname "$0")"

VERSION=$(grep -o '"version": *"[^"]*"' manifest.json | head -1 | sed 's/.*"\([0-9.]*\)"/\1/')
OUT="dist/pindl-uxp-${VERSION}.zip"

# Files that ship inside the plugin. Everything else (dist, build.sh, README)
# stays out of the bundle.
INCLUDE=(manifest.json index.html src)

echo "Validating manifest…"
node -e "JSON.parse(require('fs').readFileSync('manifest.json'))" \
  || { echo "manifest.json is not valid JSON"; exit 1; }

echo "Checking JS syntax…"
for f in src/*.js; do node --check "$f"; done

echo "Packaging v${VERSION}…"
rm -rf dist
mkdir -p dist
# manifest.json must sit at the archive ROOT (not nested in a folder).
zip -r -q "$OUT" "${INCLUDE[@]}" -x '*.DS_Store'

echo "Built $OUT"
echo "Next: load in UXP Developer Tool, or Package there to get the signed .ccx for QA."
