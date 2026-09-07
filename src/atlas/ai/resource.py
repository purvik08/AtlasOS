"""System resource monitor and Out-Of-Memory (OOM) guard for Atlas OS.

Checks available system RAM and CPU load before loading model files into memory.
"""

from __future__ import annotations

import logging

import psutil

logger = logging.getLogger(__name__)


class ResourceLimitError(RuntimeError):
    """Raised when loading a model would exceed system RAM thresholds."""


class ResourceManager:
    """Monitors system resources (RAM, CPU) and enforces allocation limits.

    Parameters
    ----------
    max_ram_percent:
        Maximum allowed RAM usage percent threshold (default 90.0%).
    """

    def __init__(self, max_ram_percent: float = 90.0) -> None:
        self.max_ram_percent = max_ram_percent
        logger.debug("ResourceManager initialised (max_ram_percent=%.1f%%).", max_ram_percent)

    def get_system_resources(self) -> dict[str, float]:
        """Return current RAM and CPU metrics."""
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)
        return {
            "ram_used_bytes": float(mem.used),
            "ram_total_bytes": float(mem.total),
            "ram_available_bytes": float(mem.available),
            "ram_percent": float(mem.percent),
            "cpu_percent": float(cpu),
        }

    def check_allocation_safety(self, required_bytes: int = -1) -> None:
        """Verify that allocating *required_bytes* won't exceed RAM limits.

        Parameters
        ----------
        required_bytes:
            Estimated size in bytes required for allocation. ``-1`` if unknown.

        Raises
        ------
        ResourceLimitError
            If current RAM usage exceeds ``max_ram_percent`` or if available
            RAM is insufficient for *required_bytes*.
        """
        metrics = self.get_system_resources()
        if metrics["ram_percent"] >= self.max_ram_percent:
            raise ResourceLimitError(
                f"System RAM usage ({metrics['ram_percent']:.1f}%) exceeds safety threshold "
                f"({self.max_ram_percent:.1f}%). Refusing to load model."
            )

        if required_bytes > 0:
            avail = metrics["ram_available_bytes"]
            if required_bytes > avail:
                raise ResourceLimitError(
                    f"Insufficient available RAM ({avail / (1024**2):.1f} MB) for "
                    f"requested model ({required_bytes / (1024**2):.1f} MB)."
                )

        logger.debug("ResourceManager: allocation check passed for %d bytes.", required_bytes)
