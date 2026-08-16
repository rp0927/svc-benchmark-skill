#!/usr/bin/env bash
# Resize screenshots before they go into report.md. Phantom page guard.
set -euo pipefail
DIR="${1:?usage: prep_images.sh <screenshots-dir>}"
if ! command -v sips >/dev/null 2>&1; then
  echo "sips not found" >&2
  exit 1
fi
shopt -s nullglob
for f in "$DIR"/*.{png,PNG,jpg,jpeg,JPG,JPEG,webp}; do
  [ -f "$f" ] || continue
  sips -Z 1400 "$f" >/dev/null
done
echo "resized in $DIR"
