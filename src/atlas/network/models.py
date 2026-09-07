"""Network data models for Atlas OS.

Shared dataclasses used by NetworkService and NetworkManagerBackend.
These are the canonical network types for the programmatic API;
the CLI layer in atlas.cli.network has its own (compatible) display types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DeviceType(str, Enum):
    """Network device type."""
    WIFI = "wifi"
    ETHERNET = "ethernet"
    LOOPBACK = "loopback"
    OTHER = "other"


class DeviceState(str, Enum):
    """NetworkManager device state (simplified subset)."""
    UNKNOWN = "unknown"
    UNMANAGED = "unmanaged"
    UNAVAILABLE = "unavailable"
    DISCONNECTED = "disconnected"
    PREPARE = "prepare"
    CONFIG = "config"
    NEED_AUTH = "need_auth"
    IP_CONFIG = "ip_config"
    IP_CHECK = "ip_check"
    SECONDARIES = "secondaries"
    ACTIVATED = "activated"
    DEACTIVATING = "deactivating"
    FAILED = "failed"


class ConnectResultCode(str, Enum):
    """Result codes for connection attempts."""
    SUCCESS = "success"
    AUTH_FAILED = "auth_failed"
    NO_SECRETS = "no_secrets"
    DEVICE_NOT_FOUND = "device_not_found"
    NETWORK_NOT_FOUND = "network_not_found"
    TIMEOUT = "timeout"
    ALREADY_CONNECTED = "already_connected"
    BACKEND_UNAVAILABLE = "backend_unavailable"
    ERROR = "error"


@dataclass
class WifiNetwork:
    """Wi-Fi access point scan result (programmatic API type)."""
    ssid: str
    bssid: str
    signal_strength: int        # 0-100 (NM percentage)
    signal_dbm: int             # dBm value
    channel: int
    frequency_mhz: int
    security: str               # e.g. "WPA2", "WPA3", "Open"
    mode: str                   # "Infrastructure", "Ad-Hoc", etc.
    in_use: bool = False        # True if currently connected

    def to_dict(self) -> dict[str, Any]:
        return {
            "ssid": self.ssid,
            "bssid": self.bssid,
            "signal_strength": self.signal_strength,
            "signal_dbm": self.signal_dbm,
            "channel": self.channel,
            "frequency_mhz": self.frequency_mhz,
            "security": self.security,
            "mode": self.mode,
            "in_use": self.in_use,
        }


@dataclass
class NetworkDevice:
    """A network interface managed by NetworkManager."""
    iface: str                  # e.g. "wlan0", "eth0"
    device_type: DeviceType
    state: DeviceState
    hw_address: str
    ip4_addresses: list[str] = field(default_factory=list)
    ip6_addresses: list[str] = field(default_factory=list)
    driver: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "iface": self.iface,
            "device_type": self.device_type.value,
            "state": self.state.value,
            "hw_address": self.hw_address,
            "ip4_addresses": self.ip4_addresses,
            "ip6_addresses": self.ip6_addresses,
            "driver": self.driver,
        }


@dataclass
class ConnectionStatus:
    """Overall network connectivity status."""
    connected: bool
    connectivity: str = "unknown"           # "none", "portal", "limited", "full", "unknown"
    primary_device: str | None = None  # iface name of the primary connection
    primary_type: DeviceType | None = None
    active_ssid: str | None = None     # Set when Wi-Fi is active

    def to_dict(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "connectivity": self.connectivity,
            "primary_device": self.primary_device,
            "primary_type": self.primary_type.value if self.primary_type else None,
            "active_ssid": self.active_ssid,
        }


@dataclass
class ConnectResult:
    """Result of a connection attempt."""
    code: ConnectResultCode
    message: str
    device: str | None = None   # iface used for the connection

    @property
    def success(self) -> bool:
        return self.code == ConnectResultCode.SUCCESS
