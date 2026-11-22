# ============================================================
# Atlas OS Image Builder — Makefile
# ============================================================
# Run from the AtlasOS repo root on the Raspberry Pi 5:
#
#   make image-setup    # clone pi-gen and link files (once)
#   make image-build    # build the .img.xz (takes ~50 min)
#   make image-clean    # wipe pi-gen work dir and start fresh
#   make image-resume   # resume a previously interrupted build
#
# The finished image lands in ~/pi-gen/deploy/AtlasOS-*.img.xz

PIGEN_DIR  := $(HOME)/pi-gen
ATLAS_DIR  := $(HOME)/AtlasOS
DEPLOY_DIR := $(PIGEN_DIR)/deploy

.PHONY: image-setup image-build image-clean image-resume help

help:
	@echo ""
	@echo "Atlas OS Image Builder"
	@echo "  make image-setup    Clone pi-gen and link Atlas stage (run once)"
	@echo "  make image-build    Build AtlasOS.img.xz (~50 min on Pi 5)"
	@echo "  make image-resume   Resume an interrupted build (skips done stages)"
	@echo "  make image-clean    Delete pi-gen work directory (full rebuild next time)"
	@echo ""

image-setup:
	@echo "==> Cloning pi-gen..."
	@if [ ! -d "$(PIGEN_DIR)" ]; then \
		git clone https://github.com/RPi-Distro/pi-gen.git $(PIGEN_DIR); \
	else \
		echo "pi-gen already cloned at $(PIGEN_DIR)."; \
	fi
	@echo "==> Linking Atlas OS config and stage..."
	@ln -sf $(ATLAS_DIR)/image/config          $(PIGEN_DIR)/config
	@ln -sf $(ATLAS_DIR)/image/stage-atlas     $(PIGEN_DIR)/stage-atlas
	@echo "==> Disabling desktop stages (3, 4, 5)..."
	@touch $(PIGEN_DIR)/stage3/SKIP \
	       $(PIGEN_DIR)/stage4/SKIP \
	       $(PIGEN_DIR)/stage5/SKIP \
	       $(PIGEN_DIR)/stage3/SKIP_IMAGES \
	       $(PIGEN_DIR)/stage4/SKIP_IMAGES \
	       $(PIGEN_DIR)/stage5/SKIP_IMAGES
	@echo "==> Installing pi-gen build dependencies..."
	@sudo apt-get install -y \
		quilt parted qemu-user-static debootstrap zerofree zip \
		dosfstools libcap2-bin grep rsync xz-utils file bc \
		binfmt-support arch-test
	@echo ""
	@echo "Setup complete. Run 'make image-build' to start the build."

image-build:
	@echo "==> Building Atlas OS image (this takes ~50 minutes)..."
	@cd $(PIGEN_DIR) && sudo bash build.sh 2>&1 | tee $(HOME)/atlas-build.log
	@echo ""
	@echo "==> Build complete. Image is at:"
	@ls -lh $(DEPLOY_DIR)/AtlasOS*.img.xz 2>/dev/null || \
		echo "No image found — check $(HOME)/atlas-build.log for errors."

image-resume:
	@echo "==> Resuming build (CLEAN=0 — skipping completed stages)..."
	@cd $(PIGEN_DIR) && sudo CLEAN=0 bash build.sh 2>&1 | tee $(HOME)/atlas-build.log

image-clean:
	@echo "==> Cleaning pi-gen work directory..."
	@cd $(PIGEN_DIR) && sudo rm -rf work/
	@echo "Done. Run 'make image-build' for a full rebuild."
