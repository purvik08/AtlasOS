# Atlas OS — Image Builder

This directory contains everything needed to build a flashable
`AtlasOS.img.xz` from scratch on a Raspberry Pi 5.

## What the image contains

| Layer | Contents |
|---|---|
| Base | Raspberry Pi OS Bookworm 64-bit (minimal, no desktop) |
| System | Python 3.12, OpenBLAS, PySide6 (from apt) |
| AI | llama-cpp-python compiled with OpenBLAS for CPU inference |
| App | Atlas OS cloned from GitHub, installed in a venv |
| Boot | Plymouth splash: dark background, cyan ATLAS OS title |
| Auto-start | X + kiosk launches on tty1 without login |
| SSH | Enabled — use it to `scp` GGUF models after flashing |

## Quick start

```bash
# On the Raspberry Pi 5, inside the AtlasOS directory:
cd ~/AtlasOS
make -f image/Makefile image-setup    # run once
make -f image/Makefile image-build    # ~50 minutes
```

The finished image is at `~/pi-gen/deploy/AtlasOS-*.img.xz`.

## Flash it

**Windows:** Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
→ Choose OS → Use custom → select the `.img.xz` file.

**Linux/Mac:**
```bash
xz -d AtlasOS-*.img.xz
sudo dd if=AtlasOS-*.img of=/dev/sdX bs=4M status=progress
sync
```

## After flashing

1. Insert SD card into Pi 5 and power on.
2. Wait ~90 seconds for first boot (SSH key regen + filesystem expand).
3. The Pi reboots automatically after first boot.
4. After second boot: Plymouth splash → kiosk appears fullscreen.
5. Copy GGUF models over SSH:
   ```bash
   scp model.gguf atlas@<PI-IP>:/home/atlas/AtlasOS/models/
   # password: atlas123
   ```
6. The kiosk's Models screen will show your files after restart.

## Build stages

| Stage | Time | What it does |
|---|---|---|
| stage0 | ~2 min | Bootstrap minimal Debian |
| stage1 | ~5 min | Base system packages |
| stage2 | ~10 min | Networking, SSH, firmware |
| 00-atlas-base | ~8 min | apt: build tools + PySide6 |
| 01-atlas-install | ~20 min | venv + llama-cpp-python compile |
| 02-atlas-kiosk | ~1 min | Auto-login + kiosk launcher |
| 03-atlas-splash | ~1 min | Plymouth theme |
| compress | ~5 min | xz compress to .img.xz |

## Troubleshooting

**Build failed in stage-atlas:**
```bash
# Resume without re-running completed stages
make -f image/Makefile image-resume
```

**Out of memory during llama-cpp compile:**
```bash
# Add swap before building
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
make -f image/Makefile image-build
```

**Kiosk doesn't start after boot:**
```bash
ssh atlas@<PI-IP>
journalctl -u atlas-kiosk -n 50
tail -f ~/AtlasOS/logs/kiosk.log
```
