#!/bin/bash -e
# Step 02-D: Write the first-boot setup script.
# Runs once after the first power-on. Sets hostname, expands filesystem,
# then deletes itself so it never runs again.

on_chroot << CHROOT
set -e

cat > /home/atlas/AtlasOS/scripts/first-boot.sh << 'FIRSTBOOT'
#!/bin/bash
# first-boot.sh — runs once after flashing, via the atlas-firstboot service.
# After completion the service disables itself so this never runs again.
LOG=/home/atlas/AtlasOS/logs/first-boot.log
exec >> "$LOG" 2>&1
set -e

echo "[$(date)] First boot starting..."

# 1. Expand the root filesystem to fill the SD card / SSD
raspi-config --expand-rootfs 2>/dev/null || true

# 2. Set hostname
hostnamectl set-hostname atlas-os

# 3. Regenerate SSH host keys (image was flashed from a master — keys must differ)
rm -f /etc/ssh/ssh_host_*
ssh-keygen -A

# 4. Create models and logs dirs (may not exist if clone happened oddly)
mkdir -p /home/atlas/AtlasOS/models
mkdir -p /home/atlas/AtlasOS/logs
mkdir -p /home/atlas/AtlasOS/data
chown -R atlas:atlas /home/atlas/AtlasOS

# 5. Write a machine-unique ID
python3 -c "import uuid; open('/home/atlas/AtlasOS/.device-id','w').write(str(uuid.uuid4()))"

echo "[$(date)] First boot complete. Device ID: $(cat /home/atlas/AtlasOS/.device-id)"

# 6. Disable this service so it never runs again
systemctl disable atlas-firstboot.service
FIRSTBOOT
chmod +x /home/atlas/AtlasOS/scripts/first-boot.sh
chown atlas:atlas /home/atlas/AtlasOS/scripts/first-boot.sh

echo "==> first-boot.sh written."
CHROOT
