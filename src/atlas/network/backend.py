"""Abstract base class for Atlas OS network backends.

The NetworkService operates exclusively through this interface.
Concrete backends (NetworkManagerBackend, etc.) implement it.
New backends can be added in v1.4.0+ without changing NetworkService.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from atlas.network.models import (
    ConnectResult,
    ConnectionStatus,
    NetworkDevice,
    WifiNetwork,
)


class NetworkBackend(ABC):
    """Abstract network backend interface.

    Implementations must be safe to call from async contexts.
    Methods may raise ``NetworkBackendError`` on unrecoverable failures.
    """

    @abstractmethod
    async def is_available(self) -> bool:
        """Return True if this backend is operational on the current system."""

    @abstractmethod
    async def scan_wifi(self, iface: str | None = None) -> list[WifiNetwork]:
        """Scan for visible Wi-Fi access points.

        Args:
            iface: Optional interface name to restrict scan (e.g. ``"wlan0"``).

        Returns:
            List of discovered access points, sorted by signal strength (desc).
        """

    @abstractmethod
    async def list_devices(self) -> list[NetworkDevice]:
        """Return all network devices managed by this backend."""

    @abstractmethod
    async def connect_wifi(
        self,
        ssid: str,
        password: str | None = None,
        iface: str | None = None,
    ) -> ConnectResult:
        """Connect to a Wi-Fi network.

        Args:
            ssid:     Target SSID.
            password: WPA/WPA2 passphrase (omit for open networks).
            iface:    Optional interface to use; backend picks one if ``None``.

        Returns:
            ``ConnectResult`` describing success or failure.
        """

    @abstractmethod
    async def disconnect(self, iface: str | None = None) -> bool:
        """Disconnect the active Wi-Fi connection.

        Args:
            iface: Interface to disconnect; disconnects first Wi-Fi iface if ``None``.

        Returns:
            ``True`` if the disconnect was issued successfully.
        """

    @abstractmethod
    async def connection_status(self) -> ConnectionStatus:
        """Return the current overall network connectivity status."""


class NetworkBackendError(RuntimeError):
    """Raised when a backend operation fails unrecoverably."""
