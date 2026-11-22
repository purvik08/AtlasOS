#!/bin/bash -e
# Step 02-E: Install systemd service units.

on_chroot << CHROOT
set -e

# ----------------------------------------------------------------
# atlas-firstboot.service — runs first-boot.sh once after flashing
# ----------------------------------------------------------------
cat > /etc/systemd/system/atlas-firstboot.service << 'UNIT'
[Unit]
Description=Atlas OS First Boot Setup
After=network.target
ConditionPathExists=/home/atlas/AtlasOS/scripts/first-boot.sh

[Service]
Type=oneshot
User=root
ExecStart=/home/atlas/AtlasOS/scripts/first-boot.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
UNIT

# ----------------------------------------------------------------
# atlas-kiosk.service — restarts the kiosk if it crashes outside X
# This is a fallback; primary launch is via .bash_profile + startx.
# When the graphical target is available this ensures the kiosk
# comes back up after a crash that also kills X.
# ----------------------------------------------------------------
cat > /etc/systemd/system/atlas-kiosk.service << 'UNIT'
[Unit]
Description=Atlas OS Kiosk UI
After=graphical.target network.target
Wants=graphical.target
PartOf=graphical.target

[Service]
Type=simple
User=atlas
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/atlas/.Xauthority
Environment=ATLAS_KIOSK_FULLSCREEN=1
Environment=ATLAS_MODELS_DIR=/home/atlas/AtlasOS/models
WorkingDirectory=/home/atlas/AtlasOS
ExecStartPre=/bin/sleep 3
ExecStart=/home/atlas/AtlasOS/.venv/bin/python -m atlas.ui.kiosk.main
Restart=on-failure
RestartSec=5
StandardOutput=append:/home/atlas/AtlasOS/logs/kiosk.log
StandardError=append:/home/atlas/AtlasOS/logs/kiosk.log

[Install]
WantedBy=graphical.target
UNIT

# ----------------------------------------------------------------
# Enable both services
# ----------------------------------------------------------------
systemctl enable atlas-firstboot.service
systemctl enable atlas-kiosk.service

echo "==> Systemd service units installed and enabled."
CHROOT
