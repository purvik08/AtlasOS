#!/bin/bash -e
# Step 02-C: Write the kiosk launcher script that X runs on startup.

on_chroot << CHROOT
set -e

mkdir -p /home/atlas/AtlasOS/scripts

cat > /home/atlas/AtlasOS/scripts/start-kiosk.sh << 'KIOSK'
#!/bin/bash
# start-kiosk.sh — launched by startx from .bash_profile
# Runs inside the X session. openbox manages window state.
set -e

# ----------------------------------------------------------------
# Window manager (no decorations, fullscreen for all windows)
# ----------------------------------------------------------------
openbox &

# ----------------------------------------------------------------
# Disable cursor, screen blanking, and power saving — kiosk mode
# ----------------------------------------------------------------
unclutter -idle 1 -root &
xset s off
xset s noblank
xset -dpms

# ----------------------------------------------------------------
# Display resolution — Pi Touch Display 2 (1280x720)
# Try both DSI (ribbon cable) and HDMI outputs
# ----------------------------------------------------------------
xrandr --output DSI-1  --mode 1280x720 2>/dev/null || true
xrandr --output HDMI-1 --mode 1280x720 2>/dev/null || true
xrandr --output HDMI-A-1 --mode 1280x720 2>/dev/null || true

# Wait for the display to settle after resolution change
sleep 1

# ----------------------------------------------------------------
# Launch Atlas OS kiosk — restarts automatically if it crashes
# ----------------------------------------------------------------
while true; do
    ATLAS_KIOSK_FULLSCREEN=1 \
    ATLAS_MODELS_DIR=/home/atlas/AtlasOS/models \
    /home/atlas/AtlasOS/.venv/bin/python -m atlas.ui.kiosk.main \
        >> /home/atlas/AtlasOS/logs/kiosk.log 2>&1
    echo "[$(date)] Kiosk exited. Restarting in 2s..." \
        >> /home/atlas/AtlasOS/logs/kiosk.log
    sleep 2
done
KIOSK
chmod +x /home/atlas/AtlasOS/scripts/start-kiosk.sh
chown atlas:atlas /home/atlas/AtlasOS/scripts/start-kiosk.sh

echo "==> start-kiosk.sh written."
CHROOT
