#!/usr/bin/env bash
# Capture desktop + mobile screenshots of the exact $CAPTURE_URL into $CAPTURE_DIR.
# Leaves the app server running; only closes its own browser.
# Exit 75 = temporary navigation/browser infrastructure failure.
# Exit 1  = script usage error or rendering defect.
set -euo pipefail

/usr/bin/time -p bash -c 'echo "capture starting"'
if [[ -z "${CAPTURE_URL:-}" ]]; then echo 'CAPTURE_URL is required.' >&2; exit 1; fi
if [[ -z "${CAPTURE_DIR:-}" ]]; then echo 'CAPTURE_DIR is required.' >&2; exit 1; fi
: "${RUNTIME_DIR:=/home/runner/work/_temp/omgithub-runtime}"

/usr/bin/time -p mkdir -p "$CAPTURE_DIR"
/usr/bin/time -p bash -c 'echo "url: $0"' "$CAPTURE_URL"
/usr/bin/time -p bash -c 'echo "dir: $0"' "$CAPTURE_DIR"
/usr/bin/time -p test -f "$RUNTIME_DIR/scripts/default-capture.mjs"

/usr/bin/time -p node "$RUNTIME_DIR/scripts/default-capture.mjs"
status=$?
/usr/bin/time -p bash -c 'echo "capture helper exit: $0"' "$status"
if [[ "$status" -eq 75 ]]; then exit 75; fi
if [[ "$status" -ne 0 ]]; then exit 1; fi

/usr/bin/time -p test -s "$CAPTURE_DIR/final-desktop.png"
/usr/bin/time -p test -s "$CAPTURE_DIR/final-mobile.png"
/usr/bin/time -p ls -la "$CAPTURE_DIR"
/usr/bin/time -p bash -c 'echo "capture done"'
