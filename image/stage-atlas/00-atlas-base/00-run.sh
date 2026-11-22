#!/bin/bash -e
# Step 00: Install system packages needed by Atlas OS.
# PySide6 must come from apt because there is no ARM64 pip wheel.

on_chroot << CHROOT
set -e

apt-get update

# Build tools (needed to compile llama-cpp-python inside the chroot)
apt-get install -y --no-install-recommends \
    git \
    cmake \
    build-essential \
    ninja-build \
    libopenblas-dev \
    libopenblas0 \
    pkg-config \
    python3-pip \
    python3-venv \
    python3-dev \
    openssl \
    ca-certificates \
    libssl-dev \
    curl \
    wget \
    unzip

# X11 / display (minimal — no full desktop)
apt-get install -y --no-install-recommends \
    xserver-xorg-core \
    xserver-xorg-input-all \
    xserver-xorg-video-fbdev \
    xserver-xorg-video-modesetting \
    x11-xserver-utils \
    xinit \
    openbox \
    unclutter

# Plymouth boot splash
apt-get install -y --no-install-recommends \
    plymouth \
    plymouth-themes

# PySide6 from apt (no usable ARM pip wheel exists for Pi OS Bookworm)
apt-get install -y --no-install-recommends \
    python3-pyside6.qtcore \
    python3-pyside6.qtgui \
    python3-pyside6.qtqml \
    python3-pyside6.qtquick \
    python3-pyside6.qtquickcontrols2 \
    python3-pyside6.qtwidgets \
    python3-pyside6.qtnetwork

# Runtime utilities
apt-get install -y --no-install-recommends \
    policykit-1 \
    dbus-x11 \
    libgl1-mesa-dri \
    libgles2-mesa \
    fonts-noto-core \
    sudo \
    htop \
    nano \
    openssh-server \
    psmisc \
    procps

apt-get clean
rm -rf /var/lib/apt/lists/*
CHROOT
