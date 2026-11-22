#!/bin/bash -e
# Step 02-A: Configure auto-login on tty1 and disable unused services.

on_chroot << CHROOT
set -e

# ----------------------------------------------------------------
# Auto-login: atlas user logs in on tty1 without a password prompt.
# getty@tty1 is the standard console login service on systemd.
# ----------------------------------------------------------------
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf << UNIT
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin atlas --noclear %I \$TERM
Type=simple
UNIT

# ----------------------------------------------------------------
# Disable services that waste RAM and CPU on a kiosk device
# ----------------------------------------------------------------
systemctl disable bluetooth   2>/dev/null || true
systemctl disable avahi-daemon 2>/dev/null || true
systemctl disable triggerhappy 2>/dev/null || true
systemctl disable apt-daily.service 2>/dev/null || true
systemctl disable apt-daily-upgrade.service 2>/dev/null || true
systemctl disable man-db.timer 2>/dev/null || true

# ----------------------------------------------------------------
# Enable SSH so models can be transferred after flashing
# ----------------------------------------------------------------
systemctl enable ssh 2>/dev/null || true

echo "==> Auto-login and service config complete."
CHROOT
