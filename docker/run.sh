#!/bin/bash
# Bring up the pfc-mcp dev container with the right ports/volumes/platform.
# Wraps `docker compose` so the long flag list lives in docker-compose.yml.
#
# Usage:  ./docker/run.sh           # console mode (default, faster)
#         ./docker/run.sh --gui     # also start X stack + noVNC
#
# Run from the repo root.

set -e

COMPOSE_FILE="$(dirname "$0")/docker-compose.yml"

# Parse --gui flag; everything else is passed through to compose.
if [ "${1:-}" = "--gui" ]; then
    export PFC_GUI=1
    shift
fi

# Always start from a clean slate. Any leftover container from a previous
# run (e.g. stopped via Ctrl-C without `compose down`) keeps its /tmp, and
# Xvfb refuses to take :1 because /tmp/.X1-lock is still there. Tearing
# down first costs ~1-2 s and only removes the container/network -- host
# volumes (workspace, bridge source) are untouched.
docker compose -f "$COMPOSE_FILE" down --remove-orphans 2>/dev/null || true

echo "[run.sh] Bringing up pfc-mcp..."
if [ "${PFC_GUI:-}" = "1" ]; then
    echo "  GUI:    http://localhost:6080/vnc.html"
fi
echo "  bridge: http://localhost:9001"
echo "  stop with Ctrl-C"
echo ""

exec docker compose -f "$COMPOSE_FILE" up
