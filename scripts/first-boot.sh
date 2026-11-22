#!/bin/bash
# first-boot.sh
# Runs ONCE after a fresh flash via atlas-firstboot.service.
# Disables itself after completing so it never runs again.

LOG=/home/atlas/AtlasOS/logs/first-boot.log
exec >> "$LOG" 2>&1
set -e

echo "========================================"
echo "  Atlas OS First Boot — $(date)"
echo "========================================"

# 1. Expand root filesystem to fill the full SD card / SSD
raspi-config --expand-rootfs 2>/dev/null || \
    echo "WARNING: raspi-config expand-rootfs failed (non-fatal)."

# 2. Hostname
hostnamectl set-hostname atlas-os

# 3. Regenerate SSH host keys — each device must have unique keys
rm -f /etc/ssh/ssh_host_*
ssh-keygen -A
echo "SSH host keys regenerated."

# 4. Ensure directory structure is present
mkdir -p /home/atlas/AtlasOS/{models,logs,data,plugins}
chown -R atlas:atlas /home/atlas/AtlasOS

# 5. Write a unique device ID
python3 -c \
  "import uuid; open('/home/atlas/AtlasOS/.device-id','w').write(str(uuid.uuid4()))"
echo "Device ID: $(cat /home/atlas/AtlasOS/.device-id)"

# 6. Self-disable — will not run again after this reboot
systemctl disable atlas-firstboot.service
echo "atlas-firstboot.service disabled."

echo "First boot complete. Rebooting in 3s..."
sleep 3
reboot
