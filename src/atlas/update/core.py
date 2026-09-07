"""Update system for Atlas OS.

Provides GitHub releases checking, download, verification, and installation.
"""

from __future__ import annotations

import hashlib
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ReleaseInfo:
    """GitHub release information."""
    version: str
    tag_name: str
    name: str
    body: str
    published_at: str
    prerelease: bool
    draft: bool
    assets: list[dict[str, Any]]
    html_url: str

    @classmethod
    def from_github_api(cls, data: dict[str, Any]) -> ReleaseInfo:
        return cls(
            version=data.get("tag_name", "").lstrip("v"),
            tag_name=data.get("tag_name", ""),
            name=data.get("name", ""),
            body=data.get("body", ""),
            published_at=data.get("published_at", ""),
            prerelease=data.get("prerelease", False),
            draft=data.get("draft", False),
            assets=data.get("assets", []),
            html_url=data.get("html_url", ""),
        )


@dataclass
class ReleaseAsset:
    """Release asset with metadata."""
    name: str
    size: int
    download_url: str
    content_type: str
    checksum: str | None = None
    checksum_type: str = "sha256"


class UpdateManager:
    """Manages Atlas OS updates from GitHub releases."""

    def __init__(
        self,
        repo: str = "atlas-os/atlas-os",
        current_version: str = "0.1.0",
        install_dir: str | Path | None = None,
    ) -> None:
        self.repo = repo
        self.current_version = current_version
        self.install_dir = Path(install_dir) if install_dir else Path(sys.prefix)
        self.api_base = f"https://api.github.com/repos/{repo}"
        self.releases_url = f"{self.api_base}/releases"

    async def check_for_updates(self, include_prerelease: bool = False) -> ReleaseInfo | None:
        """Check for available updates."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.releases_url}/latest")
                if response.status_code == 404:
                    # No releases
                    return None
                response.raise_for_status()
                release = ReleaseInfo.from_github_api(response.json())

                if release.prerelease and not include_prerelease:
                    return None

                if self._version_compare(release.version, self.current_version) <= 0:
                    return None

                return release
        except Exception:
            logger.exception("Failed to check for updates")
            return None

    async def list_releases(
        self, limit: int = 10, include_prerelease: bool = False
    ) -> list[ReleaseInfo]:
        """List recent releases."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                params = {"per_page": limit}
                response = await client.get(self.releases_url, params=params)
                response.raise_for_status()
                releases = []
                for release_data in response.json():
                    release = ReleaseInfo.from_github_api(release_data)
                    if release.prerelease and not include_prerelease:
                        continue
                    releases.append(release)
                return releases
        except Exception:
            logger.exception("Failed to list releases")
            return []

    def _version_compare(self, v1: str, v2: str) -> int:
        """Compare version strings. Returns 1 if v1 > v2, -1 if v1 < v2, 0 if equal."""
        def parse(v: str) -> list[int]:
            return [int(x) for x in v.split(".")]

        p1, p2 = parse(v1), parse(v2)
        for a, b in zip(p1, p2, strict=False):
            if a > b:
                return 1
            if a < b:
                return -1
        if len(p1) > len(p2):
            return 1
        if len(p1) < len(p2):
            return -1
        return 0

    def _get_platform_asset_name(self) -> str:
        """Determine the appropriate asset name for current platform."""
        system = platform.system().lower()
        machine = platform.machine().lower()

        if system == "linux":
            if "aarch64" in machine or "arm64" in machine:
                return "atlas-os-linux-arm64"
            return "atlas-os-linux-amd64"
        elif system == "darwin":
            if "arm64" in machine:
                return "atlas-os-macos-arm64"
            return "atlas-os-macos-amd64"
        elif system == "windows":
            return "atlas-os-windows-amd64.exe"
        return "atlas-os"

    async def download_release(
        self,
        release: ReleaseInfo,
        target_dir: str | Path | None = None,
        verify_checksum: bool = True,
    ) -> Path:
        """Download and verify release asset."""
        asset_name = self._get_platform_asset_name()

        # Find matching asset
        asset = None
        for a in release.assets:
            if asset_name in a.get("name", ""):
                asset = ReleaseAsset(
                    name=a["name"],
                    size=a["size"],
                    download_url=a["browser_download_url"],
                    content_type=a["content_type"],
                )
                break

        if not asset:
            # Try to find checksum file
            for a in release.assets:
                if a["name"].endswith(".sha256") or a["name"].endswith(".sha256sum"):
                    # Could parse checksum file
                    pass
            raise ValueError(f"No suitable asset found for platform: {asset_name}")

        if target_dir:
            target_dir = Path(target_dir)
        else:
            target_dir = Path(tempfile.gettempdir()) / "atlas-update"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / asset.name

        logger.info("Downloading %s (%d bytes)", asset.name, asset.size)

        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("GET", asset.download_url) as response:
                response.raise_for_status()
                with target_path.open("wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)

        # Verify checksum if available
        if verify_checksum:
            checksum_file = None
            for a in release.assets:
                if a["name"] == f"{asset.name}.sha256" or a["name"] == "SHA256SUMS":
                    checksum_file = a
                    break

            if checksum_file:
                await self._verify_checksum(target_path, checksum_file, client)

        return target_path

    async def _verify_checksum(
        self,
        file_path: Path,
        checksum_asset: dict[str, Any],
        client: httpx.AsyncClient,
    ) -> None:
        """Verify file checksum against checksum file."""
        # Download checksum file
        async with client.stream("GET", checksum_asset["browser_download_url"]) as response:
            response.raise_for_status()
            checksum_content = (await response.aread()).decode().strip()

        # Parse checksum (format: "hash  filename" or just "hash")
        expected_hash = None
        for line in checksum_content.split("\n"):
            if file_path.name in line:
                parts = line.split()
                if parts:
                    expected_hash = parts[0]
                    break

        if not expected_hash:
            logger.warning("No checksum found for %s", file_path.name)
            return

        # Calculate actual hash
        hasher = hashlib.sha256()
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        actual_hash = hasher.hexdigest()

        if actual_hash.lower() != expected_hash.lower():
            raise ValueError(
                f"Checksum mismatch for {file_path.name}: "
                f"expected {expected_hash}, got {actual_hash}"
            )

        logger.info("Checksum verified for %s", file_path.name)

    def install_release(self, asset_path: Path) -> bool:
        """Install downloaded release asset."""
        system = platform.system().lower()

        try:
            if system == "linux" or system == "darwin":
                return self._install_unix(asset_path)
            elif system == "windows":
                return self._install_windows(asset_path)
            else:
                logger.error("Unsupported platform for installation: %s", system)
                return False
        except Exception:
            logger.exception("Installation failed")
            return False

    def _install_unix(self, asset_path: Path) -> bool:
        """Install on Unix-like systems."""
        # Make executable
        asset_path.chmod(0o755)

        # Determine install location
        if self.install_dir == Path(sys.prefix):
            # System-wide install (requires sudo)
            target = Path("/usr/local/bin/atlas")
            if target.exists() or not os.access("/usr/local/bin", os.W_OK):
                # Use sudo
                result = subprocess.run(
                    ["sudo", "cp", str(asset_path), str(target)],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    logger.error("sudo install failed: %s", result.stderr)
                    return False
            else:
                shutil.copy2(asset_path, target)
        else:
            # User install
            target = self.install_dir / "bin" / "atlas"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(asset_path, target)

        logger.info("Installed to %s", target)
        return True

    def _install_windows(self, asset_path: Path) -> bool:
        """Install on Windows."""
        # On Windows, we typically use pip or winget
        # For direct binary, copy to a directory in PATH
        install_str = str(self.install_dir)
        if "Scripts" in install_str:
            target_dir = self.install_dir / "Scripts"
        else:
            target_dir = self.install_dir
        target = target_dir / "atlas.exe"
        target_dir.mkdir(parents=True, exist_ok=True)

        try:
            shutil.copy2(asset_path, target)
            logger.info("Installed to %s", target)
            return True
        except Exception as exc:
            logger.error("Windows install failed: %s", exc)
            return False

    async def update(self, include_prerelease: bool = False) -> bool:
        """Check for updates and install if available."""
        console = logging.getLogger("atlas.update")

        console.info("Checking for updates...")
        release = await self.check_for_updates(include_prerelease)

        if not release:
            console.info("No updates available (current: %s)", self.current_version)
            return False

        console.info("Update available: %s -> %s", self.current_version, release.version)
        console.info("Release notes:\n%s", release.body[:500])

        # Download
        console.info("Downloading release...")
        asset_path = await self.download_release(release)

        # Install
        console.info("Installing...")
        success = self.install_release(asset_path)

        if success:
            console.info("Update complete! Restart Atlas OS to use version %s", release.version)
        else:
            console.error("Update failed")

        return success


async def check_github_releases(repo: str, current_version: str) -> ReleaseInfo | None:
    """Quick check for updates."""
    manager = UpdateManager(repo=repo, current_version=current_version)
    return await manager.check_for_updates()


async def download_and_install(
    repo: str,
    current_version: str,
    version: str | None = None,
) -> bool:
    """Download and install specific or latest version."""
    manager = UpdateManager(repo=repo, current_version=current_version)

    if version:
        # Get specific release
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{manager.releases_url}/tags/v{version}")
            response.raise_for_status()
            release = ReleaseInfo.from_github_api(response.json())
    else:
        release = await manager.check_for_updates()

    if not release:
        return False

    asset_path = await manager.download_release(release)
    return manager.install_release(asset_path)