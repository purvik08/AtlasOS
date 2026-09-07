"""Atlas OS network module.

Primary backend: NetworkManager via DBus (v1.3.0+).

Public API: ``NetworkService`` facade for programmatic network operations.
CLI commands in ``atlas.cli.network`` remain unchanged.
"""

from __future__ import annotations

from atlas.network.backend import NetworkBackend, NetworkBackendError
from atlas.network.models import (
    ConnectResult,
    ConnectResultCode,
    ConnectionStatus,
    DeviceState,
    DeviceType,
    NetworkDevice,
    WifiNetwork,
)
from atlas.network.nm_backend import NetworkManagerBackend
from atlas.network.service import NetworkService

__all__ = [
    "NetworkService",
    "NetworkBackend",
    "NetworkBackendError",
    "NetworkManagerBackend",
    "WifiNetwork",
    "NetworkDevice",
    "ConnectionStatus",
    "ConnectResult",
    "ConnectResultCode",
    "DeviceType",
    "DeviceState",
]
