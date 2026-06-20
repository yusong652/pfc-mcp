#!/bin/bash
# Container entrypoint. Brings up itasca-mcp-bridge inside PFC's embedded Python.
#
# Default (console mode, lighter):
#   pfc3d9_console + bridge with blocking task pump.
#   No X stack started -- http://localhost:9001 only.
#
# GUI mode (set PFC_GUI=1):
#   In-container X stack (Xvfb + fluxbox + x11vnc + noVNC) + pfc3d9_gui
#   with bridge on a QTimer pump. Adds http://localhost:6080/vnc.html.
#
# Software GL via llvmpipe (no GPU passthrough on Docker-on-Mac).

set -e

# pfc3d9_*  resolves project/data paths against CWD. Sit in the user
# workspace so saves and scratch files land on the host-mounted volume,
# not in the bridge install dir.
cd /workspace 2>/dev/null || true

# Bootstrap that starts the bridge inside PFC's embedded Python. The pump
# mode must be explicit: pfc3d9_console has a live QCoreApplication but
# never runs its event loop, so mode=auto (bridge >= 0.1.4, PySide6 probe)
# would attach a QTimer that never fires and return from start(), parking
# the main thread at the console prompt -- which starves every bridge
# thread and leaves http://:9001 accepting TCP but never answering.
BRIDGE_MODE=console
if [ "${PFC_GUI:-}" = "1" ]; then
    BRIDGE_MODE=gui
fi
BOOTSTRAP=/tmp/itasca_mcp_bridge_start.py
cat > "$BOOTSTRAP" << PYEOF
import itasca_mcp_bridge
itasca_mcp_bridge.start(host="0.0.0.0", port=9001, mode="${BRIDGE_MODE}")
PYEOF

# ── GUI mode ──────────────────────────────────────────────────
if [ "${PFC_GUI:-}" = "1" ]; then
    export DISPLAY=:1
    export LIBGL_ALWAYS_SOFTWARE=1
    export QT_X11_NO_MITSHM=1
    # pfc3d9_gui embeds Qt WebEngine; its Chromium zygote refuses to run as
    # root without --no-sandbox. We're already inside Docker isolation, so
    # disabling the redundant sandbox is fine.
    export QTWEBENGINE_DISABLE_SANDBOX=1

    # Clear stale X11 lock + socket from a previous run (compose may keep
    # /tmp across restarts; without this Xvfb refuses :1 with "Server is
    # already active for display 1").
    rm -f /tmp/.X1-lock /tmp/.X11-unix/X1

    Xvfb :1 -screen 0 1280x800x24 -nolisten tcp &
    for _ in $(seq 1 30); do
        if xdpyinfo -display :1 >/dev/null 2>&1; then
            break
        fi
        sleep 0.1
    done

    fluxbox >/dev/null 2>&1 &
    x11vnc -display :1 -forever -shared -nopw -quiet -rfbport 5900 >/dev/null 2>&1 &
    websockify --web=/usr/share/novnc 6080 localhost:5900 >/dev/null 2>&1 &

    echo "================================================================"
    echo "  GUI:     http://localhost:6080/vnc.html"
    echo "  bridge:  http://localhost:9001"
    echo "================================================================"

    if [ "$#" -eq 0 ]; then
        exec pfc3d9_gui "$BOOTSTRAP"
    else
        exec pfc3d9_gui "$@"
    fi
fi

# ── Console mode (default) ────────────────────────────────────
echo "================================================================"
echo "  bridge:  http://localhost:9001"
echo "  (set PFC_GUI=1 to also expose the GUI via noVNC)"
echo "================================================================"

if [ "$#" -eq 0 ]; then
    exec pfc3d9_console "$BOOTSTRAP"
else
    exec pfc3d9_console "$@"
fi
