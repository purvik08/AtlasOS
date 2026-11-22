#!/bin/bash -e
# Step 03: Install Atlas OS Plymouth boot splash theme.

# Copy theme files into the chroot
install -d "${ROOTFS_DIR}/usr/share/plymouth/themes/atlas-splash"
install -m 644 \
    "${STAGE_DIR}/files/atlas-splash/atlas-splash.script" \
    "${ROOTFS_DIR}/usr/share/plymouth/themes/atlas-splash/"
install -m 644 \
    "${STAGE_DIR}/files/atlas-splash/atlas-splash.plymouth" \
    "${ROOTFS_DIR}/usr/share/plymouth/themes/atlas-splash/"

on_chroot << CHROOT
set -e

# Register and activate the Atlas OS Plymouth theme
update-alternatives \
    --install /usr/share/plymouth/themes/default.plymouth \
    default.plymouth \
    /usr/share/plymouth/themes/atlas-splash/atlas-splash.plymouth \
    200

update-alternatives \
    --set default.plymouth \
    /usr/share/plymouth/themes/atlas-splash/atlas-splash.plymouth

# Rebuild the initramfs so Plymouth is embedded in it
update-initramfs -u 2>/dev/null || true

echo "==> Plymouth Atlas splash theme installed."
CHROOT

# ----------------------------------------------------------------
# Patch /boot/firmware/cmdline.txt to enable quiet splash boot.
# The file is on the host-side FAT partition, not inside the chroot.
# ----------------------------------------------------------------
CMDLINE="${ROOTFS_DIR}/boot/firmware/cmdline.txt"
if [ -f "$CMDLINE" ]; then
    if ! grep -q "quiet splash" "$CMDLINE"; then
        sed -i 's/$/ quiet splash plymouth.ignore-serial-consoles/' "$CMDLINE"
        echo "==> cmdline.txt patched: quiet splash enabled."
    else
        echo "==> cmdline.txt already has quiet splash."
    fi
else
    echo "WARNING: cmdline.txt not found at $CMDLINE — splash may not show."
fi
