"""Atlas Update module."""

from __future__ import annotations

from atlas.update.core import ReleaseInfo, UpdateManager, download_and_install

__all__ = ["UpdateManager", "download_and_install", "ReleaseInfo"]
