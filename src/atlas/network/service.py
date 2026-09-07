"""High-level NetworkService facade for Atlas OS.

Delegates all low-level operations to a pluggable NetworkBackend.
Default backend: NetworkManagerBackend on Linux (if DBus is available),
SystemNetworkBackend fallback on Windows/macOS/other.
"""

from __future__ import annotations

import logging
from typing import Any

from atlas.network.backend import NetworkBackend, NetworkBackendError
from atlas.network.models import (
    ConnectResult,
    ConnectionStatus,
    NetworkDevice,
    WifiNetwork,
)

logger = logging.getLogger(__name__)


class NetworkService:
    """Programmatic network management service for Atlas OS."""

    def __init__(self, backend: NetworkBackend | None = None) -> None:
        if backend is not None:
            self._backend = backend
        else:
            from atlas.network.system_backend import SystemNetworkBackend
            self._backend = SystemNetworkBackend()
        self._available: bool | None = None

    @property
    def backend(self) -> NetworkBackend:
        return self._backend

    async def is_available(self) -> bool:
        """Check if backend is available (caches result)."""
        if self._available is None:
            try:
                self._available = await self._backend.is_available()
            except Exception as exc:
                logger.debug("Network backend availability check failed: %s", exc)
                self._available = False
        return self._available

    async def scan_wifi(self, iface: str | None = None) -> list[WifiNetwork]:
        """Scan Wi-Fi access points."""
        if not await self.is_available():
            raise NetworkBackendError("Network backend is unavailable")
        return await self._backend.scan_wifi(iface=iface)

    async def list_devices(self) -> list[NetworkDevice]:
        """List network devices."""
        if not await self.is_available():
            return []
        try:
            return await self._backend.list_devices()
        except Exception as exc:
            logger.debug("Failed to list network devices: %s", exc)
            return []

    async def connect_wifi(
        self, ssid: str, password: str | None = None, iface: str | None = None
    ) -> ConnectResult:
        """Connect to a Wi-Fi network."""
        if not await self.is_available():
            raise NetworkBackendError("Network backend is unavailable")
        return await self._backend.connect_wifi(ssid=ssid, password=password, iface=iface)

    async def disconnect(self, iface: str | None = None) -> bool:
        """Disconnect active Wi-Fi."""
        if not await self.is_available():
            return False
        try:
            return await self._backend.disconnect(iface=iface)
        except Exception:
            return False

    async def connection_status(self) -> ConnectionStatus:
        """Get current network connection status."""
        if not await self.is_available():
            return ConnectionStatus(
                connected=False,
                connectivity="unknown",
            )
        try:
            return await self._backend.connection_status()
        except Exception as exc:
            logger.debug("Failed to retrieve connection status: %s", exc)
            return ConnectionStatus(
                connected=False,
                connectivity="unknown",
            )

    async def is_connected(self) -> bool:
        """Convenience method checking if connected to internet."""
        status = await self.connection_status()
        return status.connected

    async def active_wifi_ssid(self) -> str | None:
        """Convenience method returning current Wi-Fi SSID."""
        status = await self.connection_status()
        return status.active_ssid

    def to_dict(self) -> dict[str, Any]:
        """Status dict for serialization / telemetry."""
        return {
            "backend": type(self._backend).__name__,
            "available": self._available,
        }
