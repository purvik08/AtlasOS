# AtlasOS Yocto Target: Raspberry Pi 5 ARM64

## Target Specification

| Parameter | Value |
|---|---|
| **Hardware** | Raspberry Pi 5 |
| **Architecture** | aarch64 (ARM64, 64-bit) |
| **MACHINE** | `raspberrypi5` |
| **Yocto branch** | `scarthgap` (Yocto 5.0 LTS) |
| **Base layer** | `meta-raspberrypi` |
| **Python** | 3.12+ |

> **v1.3.0 target is 64-bit only.** 32-bit Raspberry Pi support is out of scope
> and will NOT be added unless explicitly scoped for a future release.

---

## Required Yocto Layers

```
meta               # Yocto Poky core
meta-poky
meta-yocto-bsp
meta-raspberrypi   # Raspberry Pi BSP
meta-openembedded/meta-oe
meta-openembedded/meta-python
meta-openembedded/meta-networking
meta-atlas         # AtlasOS custom layer (to be created)
```

---

## `local.conf` Key Settings

```bitbake
# Raspberry Pi 5 — ARM64 only
MACHINE = "raspberrypi5"

# 64-bit userspace
DEFAULTTUNE = "cortexa76"

# Enable 64-bit kernel
ENABLE_UART = "1"
RPI_USE_U_BOOT = "0"

# NetworkManager as primary network backend
DISTRO_FEATURES:append = " wifi networkmanager"
CORE_IMAGE_EXTRA_INSTALL += "networkmanager networkmanager-nmtui"

# Python 3.12
IMAGE_INSTALL:append = " python3 python3-pip python3-setuptools"

# AtlasOS runtime
IMAGE_INSTALL:append = " atlas-os"

# systemd init system
DISTRO_FEATURES:append = " systemd"
VIRTUAL-RUNTIME_init_manager = "systemd"

# Remove sysvinit
DISTRO_FEATURES:remove = " sysvinit"
```

---

## `bblayers.conf` Example

```bitbake
BBLAYERS ?= " \
  ${BSPDIR}/sources/poky/meta \
  ${BSPDIR}/sources/poky/meta-poky \
  ${BSPDIR}/sources/poky/meta-yocto-bsp \
  ${BSPDIR}/sources/meta-raspberrypi \
  ${BSPDIR}/sources/meta-openembedded/meta-oe \
  ${BSPDIR}/sources/meta-openembedded/meta-python \
  ${BSPDIR}/sources/meta-openembedded/meta-networking \
  ${BSPDIR}/sources/meta-atlas \
"
```

---

## NetworkManager Integration

AtlasOS v1.3.0 uses NetworkManager as the primary network backend.
The Yocto image **must** include NetworkManager:

```bitbake
# In meta-atlas/recipes-core/images/atlas-image.bb
IMAGE_INSTALL += " \
    networkmanager \
    networkmanager-nmtui \
    wpa-supplicant \
    iw \
    wireless-regdb \
    linux-firmware-rpidistro-bcm43455 \
"
```

---

## Audio (Voice System)

```bitbake
# PipeWire (recommended for modern Raspberry Pi OS / Bookworm)
IMAGE_INSTALL += " \
    pipewire \
    pipewire-alsa \
    wireplumber \
    alsa-utils \
"
```

---

## AtlasOS Recipe Skeleton

Create `meta-atlas/recipes-atlas/atlas-os/atlas-os_1.3.0.bb`:

```bitbake
SUMMARY = "AtlasOS — Offline-first AI Edge OS for Raspberry Pi 5"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=..."

SRC_URI = "git://github.com/your-org/atlas-os.git;branch=main;protocol=https"
SRCREV = "${AUTOREV}"

S = "${WORKDIR}/git"

inherit python3native setuptools3

# Runtime dependencies
RDEPENDS:${PN} = " \
    python3 \
    python3-fastapi \
    python3-uvicorn \
    python3-pydantic \
    python3-httpx \
    python3-psutil \
    python3-cryptography \
    python3-pyjwt \
    networkmanager \
"

# Optional voice deps (add to RDEPENDS if voice is enabled)
# python3-sounddevice
# python3-faster-whisper
# python3-piper-tts

do_install:append() {
    install -d ${D}${systemd_unitdir}/system
    install -m 0644 ${S}/systemd/atlas.service \
        ${D}${systemd_unitdir}/system/atlas.service
}

SYSTEMD_SERVICE:${PN} = "atlas.service"
```

---

## Extensibility Notes

The layer structure is intentionally generic:

- `meta-atlas` can be reused for future hardware targets (e.g. NVIDIA Jetson, BeagleBone)
- The `MACHINE = "raspberrypi5"` setting is the only Pi-specific line in `local.conf`
- Switching to a new target requires updating `MACHINE`, `DEFAULTTUNE`, and BSP layers only

---

## Build Commands

```bash
# Source the Yocto environment
source poky/oe-init-build-env build-rpi5

# Build the AtlasOS image
bitbake atlas-image

# Flash to SD card
sudo dd if=tmp/deploy/images/raspberrypi5/atlas-image-raspberrypi5.wic \
    of=/dev/sdX bs=4M conv=fsync status=progress
```

---

## Verified Toolchain

| Component | Version |
|---|---|
| Yocto / Poky | 5.0 (scarthgap) |
| GCC | 13.x (aarch64-poky-linux) |
| Linux kernel | 6.6.x (rpi-6.6.y) |
| Python | 3.12.x |
| NetworkManager | 1.46.x |
| PipeWire | 1.x |
