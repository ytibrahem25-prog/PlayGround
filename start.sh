#!/usr/bin/env bash
# Ibrahim Amer Minecraft preview server.
# Serves the static build in ./dist in the FOREGROUND on $PORT (default 3000)
# and publishes worker metadata to $OPENCODE_WEB_DIR/deployment-output.json.
set -euo pipefail

/usr/bin/time -p bash -c 'cd "$(dirname "${BASH_SOURCE[0]}")" && pwd'
cd "$(dirname "${BASH_SOURCE[0]}")"

/usr/bin/time -p pwd
PROJECT_ROOT="$(pwd)"
/usr/bin/time -p bash -c 'echo "project root: $0"' "$PROJECT_ROOT"
PORT="${PORT:-3000}"
/usr/bin/time -p bash -c 'echo "port: $0"' "$PORT"
DIST_DIR="$PROJECT_ROOT/dist"
/usr/bin/time -p test -f "$DIST_DIR/index.html"

/usr/bin/time -p bash -c 'command -v python3'
# Static site: no npm dependencies to install and no build step required.
/usr/bin/time -p python3 --version

: "${OPENCODE_WEB_DIR:=/home/runner/work/_temp/omgithub-web}"
/usr/bin/time -p mkdir -p "$OPENCODE_WEB_DIR"
/usr/bin/time -p mkdir -p "$DIST_DIR"
/usr/bin/time -p bash -c 'printf "%s" "$0" > "$1/deployment-output.json.tmp"' \
  "$(printf '{"project":%s,"directory":%s}' \
    "$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$PROJECT_ROOT")" \
    "$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$DIST_DIR")")" \
  "$OPENCODE_WEB_DIR"
/usr/bin/time -p mv "$OPENCODE_WEB_DIR/deployment-output.json.tmp" "$OPENCODE_WEB_DIR/deployment-output.json"
/usr/bin/time -p cat "$OPENCODE_WEB_DIR/deployment-output.json"
echo "Serving $DIST_DIR on 0.0.0.0:$PORT (foreground)"
exec /usr/bin/time -p python3 -m http.server "$PORT" --directory "$DIST_DIR" --bind 0.0.0.0
