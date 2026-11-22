#!/bin/bash -e
# Step 01: Create the atlas user, clone Atlas OS, build Python venv,
#          and compile llama-cpp-python with OpenBLAS.
#
# This is the longest step (~15-20 min on Pi 5) because it compiles
# the llama.cpp C++ library from source inside the chroot.

on_chroot << CHROOT
set -e

# ----------------------------------------------------------------
# 1. Create atlas user
# ----------------------------------------------------------------
if ! id -u atlas &>/dev/null; then
    useradd -m -s /bin/bash atlas
fi
echo "atlas:atlas123" | chpasswd
usermod -aG sudo,video,audio,input,render atlas

# Allow atlas to run sudo without a password (kiosk device)
echo "atlas ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/atlas
chmod 440 /etc/sudoers.d/atlas

# ----------------------------------------------------------------
# 2. Clone Atlas OS repository
# ----------------------------------------------------------------
if [ -d /home/atlas/AtlasOS ]; then
    echo "AtlasOS already present — pulling latest..."
    cd /home/atlas/AtlasOS && git pull
else
    git clone --depth=1 https://github.com/purvik08/AtlasOS /home/atlas/AtlasOS
fi
chown -R atlas:atlas /home/atlas/AtlasOS

# ----------------------------------------------------------------
# 3. Create the Python virtual environment
#    --system-site-packages is REQUIRED: PySide6 came from apt
# ----------------------------------------------------------------
sudo -u atlas python3 -m venv /home/atlas/AtlasOS/.venv --system-site-packages
chown -R atlas:atlas /home/atlas/AtlasOS/.venv

# Upgrade pip inside the venv
sudo -u atlas /home/atlas/AtlasOS/.venv/bin/pip install --upgrade pip setuptools wheel

# ----------------------------------------------------------------
# 4. Compile and install llama-cpp-python (CPU-only, OpenBLAS)
#    CMAKE_ARGS tells cmake to link against libopenblas instead of
#    the default BLAS (which may not exist in the chroot).
# ----------------------------------------------------------------
CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS" \
    sudo -u atlas /home/atlas/AtlasOS/.venv/bin/pip install \
    "llama-cpp-python>=0.3" \
    --no-build-isolation \
    --verbose

# ----------------------------------------------------------------
# 5. Install Atlas OS (editable install — repo stays at ~/AtlasOS)
# ----------------------------------------------------------------
sudo -u atlas /home/atlas/AtlasOS/.venv/bin/pip install \
    -e "/home/atlas/AtlasOS" \
    --no-build-isolation

# ----------------------------------------------------------------
# 6. Create required directories
# ----------------------------------------------------------------
mkdir -p /home/atlas/AtlasOS/models
mkdir -p /home/atlas/AtlasOS/logs
mkdir -p /home/atlas/AtlasOS/data
chown -R atlas:atlas /home/atlas/AtlasOS

echo "==> Atlas OS installed successfully."
CHROOT
