#!/bin/bash
# start-kiosk.sh
# Launched by startx from /home/atlas/.bash_profile.
# Runs inside the X session on tty1 (physical display).
# Not meant to be called directly.

# ----------------------------------------------------------------
# Window manager — openbox, no decorations (configured via rc.xml)
# ----------------------------------------------------------------
openbox &

# ----------------------------------------------------------------
# Kiosk hardening: hide cursor, kill screensaver, disable DPMS
# ----------------------------------------------------------------
unclutter -idle 1 -root &
xset s off
xset s noblank
xset -dpms

# ----------------------------------------------------------------
# Display resolution
# Pi Touch Display 2 (DSI ribbon) = DSI-1 at 1280x720
# HDMI monitor fallback = HDMI-1 or HDMI-A-1
# ----------------------------------------------------------------
xrandr --output DSI-1    --mode 1280x720 2>/dev/null || true
xrandr --output HDMI-1   --mode 1280x720 2>/dev/null || true
xrandr --output HDMI-A-1 --mode 1280x720 2>/dev/null || true

sleep 1

# ----------------------------------------------------------------
# Atlas OS kiosk loop — restarts automatically on crash
# ----------------------------------------------------------------
while true; do
    ATLAS_KIOSK_FULLSCREEN=1 \
    ATLAS_MODELS_DIR=/home/atlas/AtlasOS/models \
    /home/atlas/AtlasOS/.venv/bin/python -m atlas.ui.kiosk.main \
        >> /home/atlas/AtlasOS/logs/kiosk.log 2>&1
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Kiosk exited. Restarting in 2s..." \
        >> /home/atlas/AtlasOS/logs/kiosk.log
    sleep 2
done
