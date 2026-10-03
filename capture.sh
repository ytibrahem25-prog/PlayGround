#!/usr/bin/env bash
# Screenshot capture for the deployed preview.
#
# Inputs (environment): CAPTURE_URL (exact URL to open), CAPTURE_DIR
# (output directory, must stay outside the project source).
# Output: final-desktop.png (1440x900) and final-mobile.png (390x844).
# Exit 75: temporary navigation/browser infrastructure failure.
# Exit 1: script usage error or rendering defect (missing/bad screenshots).
# The app server is left running; only this script's browser is closed.
# Every substantive command below is timed with /usr/bin/time -p.
set -euo pipefail

cd "$(dirname "$0")"
PROJECT_ROOT="$PWD"

if [[ -z "${CAPTURE_URL:-}" ]]; then echo "CAPTURE_URL must be set to the exact URL to capture." >&2; exit 1; fi
if [[ -z "${CAPTURE_DIR:-}" ]]; then echo "CAPTURE_DIR must be set to the screenshot output directory." >&2; exit 1; fi

# Keep capture output outside the project source tree.
/usr/bin/time -p bash -c 'case "$(realpath -m "$1")/" in "$2"/*) echo "CAPTURE_DIR must be outside the project source: $1" >&2; exit 1;; esac' _ "$CAPTURE_DIR" "$(realpath -m "$PROJECT_ROOT")"

/usr/bin/time -p mkdir -p "$CAPTURE_DIR"

# Headful chromium under Xvfb via the shared playwright runtime. The helper
# exits 75 on transient browser/navigation failures and 1 on page errors;
# with `set -e` its status propagates unchanged (time preserves it).
/usr/bin/time -p node "${RUNTIME_DIR:?RUNTIME_DIR must be set}/scripts/default-capture.mjs"

# Rendering-defect checks: both screenshots must exist, be non-empty PNGs
# with the expected viewport dimensions.
/usr/bin/time -p test -s "$CAPTURE_DIR/final-desktop.png"
/usr/bin/time -p test -s "$CAPTURE_DIR/final-mobile.png"
/usr/bin/time -p python3 - "$CAPTURE_DIR" <<'PYEOF'
import os
import struct
import sys

out = sys.argv[1]
expected = {"final-desktop.png": (1440, 900), "final-mobile.png": (390, 844)}
for name, (ew, eh) in expected.items():
    path = os.path.join(out, name)
    with open(path, "rb") as fh:
        blob = fh.read(33)
    if len(blob) < 33 or blob[:8] != b"\x89PNG\r\n\x1a\n" or blob[12:16] != b"IHDR":
        print("not a PNG: " + path)
        sys.exit(1)
    w, h = struct.unpack(">II", blob[16:24])
    print("%s: %dx%d" % (name, w, h))
    if (w, h) != (ew, eh):
        print("unexpected dimensions for %s: got %dx%d, want %dx%d" % (name, w, h, ew, eh))
        sys.exit(1)
print("screenshots verified")
PYEOF

/usr/bin/time -p ls -la "$CAPTURE_DIR"
echo "capture complete: $CAPTURE_DIR (app server left running)"
