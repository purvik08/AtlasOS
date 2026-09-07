"""NetworkManager DBus backend for Atlas OS.

Uses ``dbus-next`` (async DBus client) to communicate with the
NetworkManager system service. This is the PRIMARY network backend
for v1.3.0 on Raspberry Pi 5 / Linux.

Architecture:
    NetworkService → NetworkManagerBackend → NetworkManager DBus
                                           → Wi-Fi / Ethernet

If NetworkManager DBus is not available (non-Linux, NM not running, or
``dbus-next`` not installed) this backend reports ``is_available() == False``
and all operations return appropriate error results rather than raising.

A direct wpa_supplicant backend can be added later as an alternate
``NetworkBackend`` implementation without touching NetworkService.
"""

from __future__ import annotations

import asyncio
import logging
import platform
from typing import Any

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

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependency: dbus-next
# ---------------------------------------------------------------------------
try:
    from dbus_next.aio import MessageBus
    from dbus_next import BusType, Variant
    _DBUS_AVAILABLE = True
except ImportError:
    _DBUS_AVAILABLE = False
    logger.debug(
        "dbus-next not installed; NetworkManagerBackend will not be available. "
        "Install with: pip install dbus-next"
    )

# NetworkManager well-known DBus names / paths
_NM_BUS_NAME = "org.freedesktop.NetworkManager"
_NM_OBJECT   = "/org/freedesktop/NetworkManager"
_NM_IFACE    = "org.freedesktop.NetworkManager"
_NM_DEV_IFACE   = "org.freedesktop.NetworkManager.Device"
_NM_DEV_WIFI    = "org.freedesktop.NetworkManager.Device.Wireless"
_NM_AP_IFACE    = "org.freedesktop.NetworkManager.AccessPoint"
_NM_CONN_IFACE  = "org.freedesktop.NetworkManager.Connection.Active"
_PROP_IFACE     = "org.freedesktop.DBus.Properties"

# NM device type constants (from NM API)
_NM_DEVICE_TYPE_ETHERNET = 1
_NM_DEVICE_TYPE_WIFI     = 2
_NM_DEVICE_TYPE_LOOPBACK = 14

# NM device state constants
_NM_DEVICE_STATE: dict[int, DeviceState] = {
    0:   DeviceState.UNKNOWN,
    10:  DeviceState.UNMANAGED,
    20:  DeviceState.UNAVAILABLE,
    30:  DeviceState.DISCONNECTED,
    40:  DeviceState.PREPARE,
    50:  DeviceState.CONFIG,
    60:  DeviceState.NEED_AUTH,
    70:  DeviceState.IP_CONFIG,
    80:  DeviceState.IP_CHECK,
    90:  DeviceState.SECONDARIES,
    100: DeviceState.ACTIVATED,
    110: DeviceState.DEACTIVATING,
    120: DeviceState.FAILED,
}

# NM connectivity state constants
_NM_CONNECTIVITY: dict[int, str] = {
    0: "unknown",
    1: "none",
    2: "portal",
    3: "limited",
    4: "full",
}


class NetworkManagerBackend(NetworkBackend):
    """Primary network backend using NetworkManager over DBus.

    All public methods are async-safe and handle DBus failures gracefully.
    Production code should call ``is_available()`` once at startup to
    confirm the backend can operate.
    """

    def __init__(self) -> None:
        self._bus: Any = None   # MessageBus instance when connected
        self._nm: Any = None    # NM proxy object
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Internal DBus helpers
    # ------------------------------------------------------------------

    async def _get_bus(self) -> Any:
        """Return a connected system bus, connecting lazily."""
        if not _DBUS_AVAILABLE:
            raise NetworkBackendError(
                "dbus-next is not installed. "
                "Install with: pip install dbus-next"
            )
        if self._bus is None:
            try:
                self._bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
                logger.debug("Connected to system DBus")
            except Exception as exc:
                raise NetworkBackendError(
                    f"Cannot connect to system DBus: {exc}"
                ) from exc
        return self._bus

    async def _get_nm_proxy(self) -> Any:
        """Return the NetworkManager DBus proxy (introspected)."""
        if self._nm is not None:
            return self._nm
        bus = await self._get_bus()
        introspection = await bus.introspect(_NM_BUS_NAME, _NM_OBJECT)
        self._nm = bus.get_proxy_object(
            _NM_BUS_NAME, _NM_OBJECT, introspection
        )
        return self._nm

    async def _get_interface(self, object_path: str, iface_name: str) -> Any:
        """Get a specific interface proxy for a DBus object path."""
        bus = await self._get_bus()
        introspection = await bus.introspect(_NM_BUS_NAME, object_path)
        proxy = bus.get_proxy_object(_NM_BUS_NAME, object_path, introspection)
        return proxy.get_interface(iface_name)

    async def _get_property(
        self, object_path: str, iface_name: str, prop_name: str
    ) -> Any:
        """Read a single DBus property."""
        props = await self._get_interface(object_path, _PROP_IFACE)
        result = await props.call_get(iface_name, prop_name)
        return result.value if hasattr(result, "value") else result

    # ------------------------------------------------------------------
    # NetworkBackend interface
    # ------------------------------------------------------------------

    async def is_available(self) -> bool:
        """Return True if NetworkManager DBus is reachable."""
        if not _DBUS_AVAILABLE:
            return False
        if platform.system().lower() != "linux":
            logger.debug(
                "NetworkManagerBackend is Linux-only; "
                "current platform: %s", platform.system()
            )
            return False
        try:
            await self._get_nm_proxy()
            return True
        except Exception as exc:
            logger.warning("NetworkManager not available: %s", exc)
            return False

    async def scan_wifi(self, iface: str | None = None) -> list[WifiNetwork]:
        """Scan for Wi-Fi networks via NetworkManager DBus.

        Triggers a fresh scan on the wireless device, waits for NM to
        complete it, then reads the AccessPoint list.
        """
        try:
            devices = await self._get_wifi_devices()
            if not devices:
                logger.warning("No Wi-Fi devices found under NetworkManager")
                return []

            target_path = None
            for dev_path, dev_iface in devices:
                if iface is None or dev_iface == iface:
                    target_path = dev_path
                    break

            if target_path is None:
                logger.warning("Wi-Fi interface %r not found", iface)
                return []

            # Request a new scan
            await self._request_scan(target_path)
            # Allow NM time to complete the scan
            await asyncio.sleep(3)

            return await self._read_access_points(target_path)

        except NetworkBackendError:
            raise
        except Exception as exc:
            raise NetworkBackendError(f"Wi-Fi scan failed: {exc}") from exc

    async def list_devices(self) -> list[NetworkDevice]:
        """Return all NM-managed network devices."""
        try:
            nm = await self._get_nm_proxy()
            nm_iface = nm.get_interface(_NM_IFACE)
            device_paths = await nm_iface.call_get_devices()

            devices: list[NetworkDevice] = []
            for dev_path in device_paths:
                try:
                    dev = await self._build_network_device(dev_path)
                    devices.append(dev)
                except Exception as exc:
                    logger.debug("Skipping device %s: %s", dev_path, exc)

            return devices

        except NetworkBackendError:
            raise
        except Exception as exc:
            raise NetworkBackendError(f"Failed to list devices: {exc}") from exc

    async def connect_wifi(
        self,
        ssid: str,
        password: str | None = None,
        iface: str | None = None,
    ) -> ConnectResult:
        """Connect to a Wi-Fi SSID via NetworkManager.

        NM will create a new connection profile if none exists for this SSID.
        The ``AddAndActivateConnection`` DBus method is used so we don't need
        to manage connection profiles ourselves.
        """
        try:
            devices = await self._get_wifi_devices()
            if not devices:
                return ConnectResult(
                    code=ConnectResultCode.DEVICE_NOT_FOUND,
                    message="No Wi-Fi devices managed by NetworkManager",
                )

            dev_path, dev_iface = devices[0]
            if iface:
                matched = [(p, i) for p, i in devices if i == iface]
                if not matched:
                    return ConnectResult(
                        code=ConnectResultCode.DEVICE_NOT_FOUND,
                        message=f"Wi-Fi interface '{iface}' not found",
                    )
                dev_path, dev_iface = matched[0]

            # Build a minimal connection dictionary for AddAndActivateConnection
            conn_settings: dict[str, Any] = {
                "connection": {
                    "type": Variant("s", "802-11-wireless"),
                    "id": Variant("s", ssid),
                },
                "802-11-wireless": {
                    "ssid": Variant("ay", ssid.encode()),
                    "mode": Variant("s", "infrastructure"),
                },
                "ipv4": {"method": Variant("s", "auto")},
                "ipv6": {"method": Variant("s", "auto")},
            }

            if password:
                conn_settings["802-11-wireless-security"] = {
                    "key-mgmt": Variant("s", "wpa-psk"),
                    "psk": Variant("s", password),
                }

            nm = await self._get_nm_proxy()
            nm_iface = nm.get_interface(_NM_IFACE)

            try:
                _conn_path, _active_path = await nm_iface.call_add_and_activate_connection(
                    conn_settings, dev_path, "/"
                )
                logger.info("Connecting to %r on %s", ssid, dev_iface)
            except Exception as exc:
                err_str = str(exc).lower()
                if "secrets" in err_str or "password" in err_str or "psk" in err_str:
                    return ConnectResult(
                        code=ConnectResultCode.AUTH_FAILED,
                        message=f"Authentication failed for '{ssid}': {exc}",
                        device=dev_iface,
                    )
                return ConnectResult(
                    code=ConnectResultCode.ERROR,
                    message=f"Connection failed: {exc}",
                    device=dev_iface,
                )

            # Poll for activation (up to 30 s)
            for _ in range(30):
                await asyncio.sleep(1)
                status = await self.connection_status()
                if status.connected and status.active_ssid == ssid:
                    return ConnectResult(
                        code=ConnectResultCode.SUCCESS,
                        message=f"Connected to '{ssid}'",
                        device=dev_iface,
                    )

            return ConnectResult(
                code=ConnectResultCode.TIMEOUT,
                message=f"Timed out waiting for connection to '{ssid}'",
                device=dev_iface,
            )

        except NetworkBackendError:
            raise
        except Exception as exc:
            raise NetworkBackendError(f"connect_wifi failed: {exc}") from exc

    async def disconnect(self, iface: str | None = None) -> bool:
        """Disconnect the active Wi-Fi connection."""
        try:
            devices = await self._get_wifi_devices()
            if not devices:
                return False

            dev_path = devices[0][0]
            if iface:
                matched = [p for p, i in devices if i == iface]
                if not matched:
                    return False
                dev_path = matched[0]

            dev_iface = await self._get_interface(dev_path, _NM_DEV_IFACE)
            await dev_iface.call_disconnect()
            logger.info("Disconnected network device at %s", dev_path)
            return True

        except Exception as exc:
            logger.warning("Disconnect failed: %s", exc)
            return False

    async def connection_status(self) -> ConnectionStatus:
        """Return current NM connectivity status."""
        try:
            nm = await self._get_nm_proxy()
            nm_iface = nm.get_interface(_NM_IFACE)

            # NM state: 20=disconnected, 70=connected-local, 60=connected-site, 70=connected-global
            nm_state = await nm_iface.call_state()
            connected = nm_state >= 70

            # Connectivity: 0-4
            try:
                connectivity_val = await nm_iface.call_check_connectivity()
                connectivity = _NM_CONNECTIVITY.get(connectivity_val, "unknown")
            except Exception:
                connectivity = "unknown"

            # Primary connection device + SSID
            primary_device: str | None = None
            primary_type: DeviceType | None = None
            active_ssid: str | None = None

            try:
                active_conns = await self._get_property(
                    _NM_OBJECT, _NM_IFACE, "ActiveConnections"
                )
                for conn_path in (active_conns or []):
                    try:
                        dev_paths = await self._get_property(
                            conn_path, _NM_CONN_IFACE, "Devices"
                        )
                        if dev_paths:
                            dev_path = dev_paths[0]
                            dev_type_val = await self._get_property(
                                dev_path, _NM_DEV_IFACE, "DeviceType"
                            )
                            dev_iface_name = await self._get_property(
                                dev_path, _NM_DEV_IFACE, "Interface"
                            )
                            primary_device = dev_iface_name
                            primary_type = _nm_device_type(dev_type_val)

                            if dev_type_val == _NM_DEVICE_TYPE_WIFI:
                                try:
                                    ap_path = await self._get_property(
                                        dev_path, _NM_DEV_WIFI, "ActiveAccessPoint"
                                    )
                                    if ap_path and ap_path != "/":
                                        ssid_bytes = await self._get_property(
                                            ap_path, _NM_AP_IFACE, "Ssid"
                                        )
                                        active_ssid = bytes(ssid_bytes).decode(
                                            "utf-8", errors="replace"
                                        )
                                except Exception:
                                    pass
                            break
                    except Exception:
                        pass
            except Exception as exc:
                logger.debug("Could not read active connections: %s", exc)

            return ConnectionStatus(
                connected=connected,
                connectivity=connectivity,
                primary_device=primary_device,
                primary_type=primary_type,
                active_ssid=active_ssid,
            )

        except Exception as exc:
            logger.warning("connection_status failed: %s", exc)
            return ConnectionStatus(
                connected=False,
                connectivity="unknown",
                primary_device=None,
                primary_type=None,
                active_ssid=None,
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_wifi_devices(self) -> list[tuple[str, str]]:
        """Return list of (object_path, iface_name) for Wi-Fi devices."""
        nm = await self._get_nm_proxy()
        nm_iface = nm.get_interface(_NM_IFACE)
        device_paths = await nm_iface.call_get_devices()

        wifi_devices: list[tuple[str, str]] = []
        for dev_path in device_paths:
            try:
                dev_type = await self._get_property(
                    dev_path, _NM_DEV_IFACE, "DeviceType"
                )
                if dev_type == _NM_DEVICE_TYPE_WIFI:
                    iface_name = await self._get_property(
                        dev_path, _NM_DEV_IFACE, "Interface"
                    )
                    wifi_devices.append((dev_path, iface_name))
            except Exception:
                pass
        return wifi_devices

    async def _request_scan(self, dev_path: str) -> None:
        """Request a Wi-Fi scan on a device."""
        try:
            wifi_iface = await self._get_interface(dev_path, _NM_DEV_WIFI)
            await wifi_iface.call_request_scan({})
        except Exception as exc:
            # Scan requests can fail if a scan is already in progress
            logger.debug("RequestScan notice (non-fatal): %s", exc)

    async def _read_access_points(self, dev_path: str) -> list[WifiNetwork]:
        """Read the current AP list from a wireless device."""
        wifi_iface = await self._get_interface(dev_path, _NM_DEV_WIFI)
        ap_paths = await wifi_iface.call_get_access_points()

        # Identify currently active AP
        try:
            active_ap_path = await self._get_property(
                dev_path, _NM_DEV_WIFI, "ActiveAccessPoint"
            )
        except Exception:
            active_ap_path = None

        networks: list[WifiNetwork] = []
        for ap_path in ap_paths:
            try:
                ap = await self._build_wifi_network(
                    ap_path, in_use=(ap_path == active_ap_path)
                )
                networks.append(ap)
            except Exception as exc:
                logger.debug("Skipping AP %s: %s", ap_path, exc)

        # Sort by signal strength descending
        networks.sort(key=lambda n: n.signal_strength, reverse=True)
        return networks

    async def _build_wifi_network(
        self, ap_path: str, in_use: bool = False
    ) -> WifiNetwork:
        """Build a WifiNetwork from an AccessPoint DBus object."""
        ssid_bytes = await self._get_property(ap_path, _NM_AP_IFACE, "Ssid")
        ssid = bytes(ssid_bytes).decode("utf-8", errors="replace") if ssid_bytes else "(hidden)"

        bssid = await self._get_property(ap_path, _NM_AP_IFACE, "HwAddress")
        strength = await self._get_property(ap_path, _NM_AP_IFACE, "Strength")
        frequency = await self._get_property(ap_path, _NM_AP_IFACE, "Frequency")
        flags = await self._get_property(ap_path, _NM_AP_IFACE, "Flags")
        wpa_flags = await self._get_property(ap_path, _NM_AP_IFACE, "WpaFlags")
        rsn_flags = await self._get_property(ap_path, _NM_AP_IFACE, "RsnFlags")
        mode = await self._get_property(ap_path, _NM_AP_IFACE, "Mode")

        freq_mhz = int(frequency) if frequency else 0
        channel = _freq_to_channel(freq_mhz)
        signal_dbm = _strength_to_dbm(int(strength) if strength else 0)
        security = _determine_security(int(flags or 0), int(wpa_flags or 0), int(rsn_flags or 0))
        mode_str = _ap_mode_string(int(mode) if mode else 2)

        return WifiNetwork(
            ssid=ssid,
            bssid=bssid or "00:00:00:00:00:00",
            signal_strength=int(strength) if strength else 0,
            signal_dbm=signal_dbm,
            channel=channel,
            frequency_mhz=freq_mhz,
            security=security,
            mode=mode_str,
            in_use=in_use,
        )

    async def _build_network_device(self, dev_path: str) -> NetworkDevice:
        """Build a NetworkDevice from a Device DBus object path."""
        dev_type_val = await self._get_property(dev_path, _NM_DEV_IFACE, "DeviceType")
        iface_name = await self._get_property(dev_path, _NM_DEV_IFACE, "Interface")
        state_val = await self._get_property(dev_path, _NM_DEV_IFACE, "State")
        hw_addr = await self._get_property(dev_path, _NM_DEV_IFACE, "HwAddress")
        driver = await self._get_property(dev_path, _NM_DEV_IFACE, "Driver")

        state = _NM_DEVICE_STATE.get(int(state_val or 0), DeviceState.UNKNOWN)
        dev_type = _nm_device_type(dev_type_val)

        # IP addresses
        ip4: list[str] = []
        ip6: list[str] = []
        try:
            ip4_config_path = await self._get_property(
                dev_path, _NM_DEV_IFACE, "Ip4Config"
            )
            if ip4_config_path and ip4_config_path != "/":
                ip4 = await self._read_ip4_addresses(ip4_config_path)
        except Exception:
            pass
        try:
            ip6_config_path = await self._get_property(
                dev_path, _NM_DEV_IFACE, "Ip6Config"
            )
            if ip6_config_path and ip6_config_path != "/":
                ip6 = await self._read_ip6_addresses(ip6_config_path)
        except Exception:
            pass

        return NetworkDevice(
            iface=iface_name or dev_path,
            device_type=dev_type,
            state=state,
            hw_address=hw_addr or "",
            ip4_addresses=ip4,
            ip6_addresses=ip6,
            driver=driver or "",
        )

    async def _read_ip4_addresses(self, ip4_config_path: str) -> list[str]:
        """Read IPv4 address strings from an Ip4Config object."""
        addrs = await self._get_property(
            ip4_config_path,
            "org.freedesktop.NetworkManager.IP4Config",
            "AddressData",
        )
        result: list[str] = []
        for addr_dict in (addrs or []):
            address = addr_dict.get("address")
            prefix = addr_dict.get("prefix")
            if address:
                val = address.value if hasattr(address, "value") else address
                pfx = prefix.value if hasattr(prefix, "value") else prefix
                result.append(f"{val}/{pfx}" if pfx else str(val))
        return result

    async def _read_ip6_addresses(self, ip6_config_path: str) -> list[str]:
        """Read IPv6 address strings from an Ip6Config object."""
        addrs = await self._get_property(
            ip6_config_path,
            "org.freedesktop.NetworkManager.IP6Config",
            "AddressData",
        )
        result: list[str] = []
        for addr_dict in (addrs or []):
            address = addr_dict.get("address")
            prefix = addr_dict.get("prefix")
            if address:
                val = address.value if hasattr(address, "value") else address
                pfx = prefix.value if hasattr(prefix, "value") else prefix
                result.append(f"{val}/{pfx}" if pfx else str(val))
        return result


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def _nm_device_type(val: Any) -> DeviceType:
    v = int(val) if val is not None else 0
    if v == _NM_DEVICE_TYPE_ETHERNET:
        return DeviceType.ETHERNET
    if v == _NM_DEVICE_TYPE_WIFI:
        return DeviceType.WIFI
    if v == _NM_DEVICE_TYPE_LOOPBACK:
        return DeviceType.LOOPBACK
    return DeviceType.OTHER


def _freq_to_channel(freq_mhz: int) -> int:
    """Convert Wi-Fi frequency (MHz) to channel number."""
    if 2412 <= freq_mhz <= 2484:
        return (freq_mhz - 2407) // 5
    if 5170 <= freq_mhz <= 5825:
        return (freq_mhz - 5000) // 5
    return 0


def _strength_to_dbm(strength: int) -> int:
    """Convert NM signal strength (0-100) to approximate dBm."""
    # NM strength is percentage; rough linear conversion
    return -100 + strength


def _determine_security(flags: int, wpa_flags: int, rsn_flags: int) -> str:
    """Determine security type from NM AP flags."""
    if rsn_flags != 0:
        return "WPA2"
    if wpa_flags != 0:
        return "WPA"
    if flags & 0x1:   # NM_802_11_AP_FLAGS_PRIVACY
        return "WEP"
    return "Open"


def _ap_mode_string(mode: int) -> str:
    """Convert NM AP mode integer to string."""
    return {0: "Unknown", 1: "Ad-Hoc", 2: "Infrastructure", 3: "AP"}.get(
        mode, "Infrastructure"
    )
