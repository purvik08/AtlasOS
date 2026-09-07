"""NetworkService — public programmatic API for Atlas OS network management.

This service is the single entry point for all network operations done
by Atlas OS subsystems (AI, memory sync, OTA updates, etc.).

The CLI commands in ``atlas.cli.network`` operate independently via
subprocess (nmcli/iw/psutil) for user-facing output — they remain
unchanged. ``NetworkService`` provides the programmatic API.

Architecture:
    NetworkService
        ↓
    NetworkBackend (ABC)
        ↓
    NetworkManagerBackend (DBus)  ← primary for v1.3.0
        ↓
    NetworkManager → Wi-Fi / Ethernet

A wpa_supplicant direct backend can be swapped in as an alternative
``NetworkBackend`` without modifying this class.
"""

from __future__ import annotations

import logging
from typing import Any

from atlas.network.backend import NetworkBackend, NetworkBackendError
from atlas.network.models import (
    ConnectResult,
    ConnectResultCode,
    ConnectionStatus,
    DeviceState,
    NetworkDevice,
    WifiNetwork,
)

logger = logging.getLogger(__name__)


class NetworkService:
    """Facade over a ``NetworkBackend``.

    Usage::

        svc = NetworkService()                      # uses NM backend
        svc = NetworkService(backend=MyBackend())   # custom backend

        await svc.scan_wifi()
        await svc.connect_wifi("MyNetwork", "password")
        await svc.connection_status()
    """

    def __init__(self, backend: NetworkBackend | None = None) -> None:
        self._custom_backend = backend is not None
        if backend is not None:
            self._backend: NetworkBackend = backend
        else:
            # Default: NetworkManager (primary for v1.3.0 on Linux)
            from atlas.network.nm_backend import NetworkManagerBackend
            self._backend = NetworkManagerBackend()

        self._available: bool | None = None   # cached after first check

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------

    async def is_available(self) -> bool:
        """Return True if the network backend is operational."""
        if self._available is None:
            available = await self._backend.is_available()
            if not available and not self._custom_backend:
                from atlas.network.system_backend import SystemNetworkBackend
                self._backend = SystemNetworkBackend()
                available = await self._backend.is_available()
            self._available = available
        return self._available

    async def _require_available(self) -> None:
        """Raise ``NetworkBackendError`` if backend is not available."""
        if not await self.is_available():
            raise NetworkBackendError(
                "Network backend is not available on this system."
            )


    # ------------------------------------------------------------------
    # Wi-Fi operations
    # ------------------------------------------------------------------

    async def scan_wifi(self, iface: str | None = None) -> list[WifiNetwork]:
        """Scan for visible Wi-Fi networks.

        Args:
            iface: Optional wireless interface (e.g. ``"wlan0"``).

        Returns:
            List of networks sorted by signal strength (strongest first).

        Raises:
            NetworkBackendError: If the backend cannot perform the scan.
        """
        await self._require_available()
        networks = await self._backend.scan_wifi(iface)
        logger.debug("Wi-Fi scan found %d networks", len(networks))
        return networks

    async def connect_wifi(
        self,
        ssid: str,
        password: str | None = None,
        iface: str | None = None,
    ) -> ConnectResult:
        """Connect to a Wi-Fi network.

        Args:
            ssid:     Target SSID.
            password: WPA/WPA2/WPA3 passphrase (omit for open networks).
            iface:    Wireless interface to use; backend picks one if ``None``.

        Returns:
            ``ConnectResult`` with ``success`` property and descriptive message.
        """
        await self._require_available()
        result = await self._backend.connect_wifi(ssid, password, iface)
        if result.success:
            logger.info("Connected to Wi-Fi SSID %r", ssid)
        else:
            logger.warning(
                "Wi-Fi connection to %r failed: [%s] %s",
                ssid, result.code.value, result.message,
            )
        return result

    async def disconnect(self, iface: str | None = None) -> bool:
        """Disconnect the active Wi-Fi connection.

        Args:
            iface: Interface to disconnect (first Wi-Fi device if ``None``).

        Returns:
            ``True`` if disconnect was issued successfully.
        """
        await self._require_available()
        ok = await self._backend.disconnect(iface)
        if ok:
            logger.info("Disconnected Wi-Fi (iface=%r)", iface)
        return ok

    # ------------------------------------------------------------------
    # Status & device enumeration
    # ------------------------------------------------------------------

    async def connection_status(self) -> ConnectionStatus:
        """Return current network connectivity status.

        Always returns a ``ConnectionStatus`` — never raises on backend errors;
        instead returns a disconnected/unknown status so callers can handle
        gracefully.
        """
        try:
            await self._require_available()
            return await self._backend.connection_status()
        except NetworkBackendError as exc:
            logger.debug("connection_status unavailable: %s", exc)
            return ConnectionStatus(
                connected=False,
                connectivity="unknown",
                primary_device=None,
                primary_type=None,
                active_ssid=None,
            )

    async def list_devices(self) -> list[NetworkDevice]:
        """Return all network devices managed by the backend.

        Returns an empty list if the backend is unavailable.
        """
        try:
            await self._require_available()
            return await self._backend.list_devices()
        except NetworkBackendError as exc:
            logger.debug("list_devices unavailable: %s", exc)
            return []

    async def is_connected(self) -> bool:
        """Quick connectivity check — True if the system has network access."""
        status = await self.connection_status()
        return status.connected

    async def active_wifi_ssid(self) -> str | None:
        """Return the currently connected Wi-Fi SSID, or ``None``."""
        status = await self.connection_status()
        return status.active_ssid

    def to_dict(self) -> dict[str, Any]:
        """Return service metadata for health checks / status endpoints."""
        return {
            "backend": type(self._backend).__name__,
            "available": self._available,
        }
