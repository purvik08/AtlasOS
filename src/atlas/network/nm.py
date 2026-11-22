"""NetworkManager DBus integration for Atlas OS."""

from __future__ import annotations

import asyncio
import platform
from typing import Any

# Optional import for loguru
try:
    from loguru import logger
    LOGURU_AVAILABLE = True
except ImportError:
    LOGURU_AVAILABLE = False
    import logging
    logger = logging.getLogger(__name__)

# Check if we're on Linux (NetworkManager is Linux-specific)
_IS_LINUX = platform.system().lower() == "linux"

# Try to import DBus libraries
try:
    if _IS_LINUX:
        import dbus
        import dbus.aio
        import dbus.exceptions
        DBUS_AVAILABLE = True
    else:
        DBUS_AVAILABLE = False
except ImportError:
    DBUS_AVAILABLE = False


class NetworkManagerBackend:
    """Async wrapper for NetworkManager DBus API (org.freedesktop.NetworkManager)."""
    
    # NetworkManager DBus constants
    NM_SERVICE = "org.freedesktop.NetworkManager"
    NM_PATH = "/org/freedesktop/NetworkManager"
    NM_INTERFACE = "org.freedesktop.NetworkManager"
    
    # Device interfaces
    NM_DEVICE_INTERFACE = "org.freedesktop.NetworkManager.Device"
    NM_DEVICE_WIFI_INTERFACE = "org.freedesktop.NetworkManager.Device.Wireless"
    
    # Connection interfaces
    NM_SETTINGS_SERVICE = "org.freedesktop.NetworkManager.Settings"
    NM_SETTINGS_PATH = "/org/freedesktop/NetworkManager/Settings"
    NM_SETTINGS_INTERFACE = "org.freedesktop.NetworkManager.Settings"
    NM_CONNECTION_INTERFACE = "org.freedesktop.NetworkManager.Settings.Connection"
    
    def __init__(self) -> None:
        """Initialize NetworkManager backend."""
        self._system_bus = None
        self._nm_service = None
        self._nm_settings = None
        self._connected = False
        
    async def _initialize_dbus(self) -> bool:
        """Initialize DBus connection."""
        if not _IS_LINUX:
            if LOGURU_AVAILABLE:
                logger.warning("NetworkManager DBus only available on Linux")
            else:
                logger.warning("NetworkManager DBus only available on Linux")
            return False
            
        if not DBUS_AVAILABLE:
            if LOGURU_AVAILABLE:
                logger.error("DBus libraries not available")
            else:
                logger.error("DBus libraries not available")
            return False
            
        try:
            # Get system bus
            self._system_bus = await dbus.aio.MessageBus(
                bus=dbus.aio.BusType.SYSTEM
            ).__aenter__()
            
            # Get NetworkManager service
            self._nm_service = self._system_bus.get_proxy_object(
                self.NM_SERVICE, 
                self.NM_PATH,
                self.NM_INTERFACE
            )
            
            # Get Settings service
            self._nm_settings = self._system_bus.get_proxy_object(
                self.NM_SETTINGS_SERVICE,
                self.NM_SETTINGS_PATH,
                self.NM_SETTINGS_INTERFACE
            )
            
            self._connected = True
            if LOGURU_AVAILABLE:
                logger.info("NetworkManager DBus connection established")
            else:
                logger.info("NetworkManager DBus connection established")
            return True
            
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Failed to initialize NetworkManager DBus: {e}")
            else:
                logger.error(f"Failed to initialize NetworkManager DBus: {e}")
            return False
    
    async def _ensure_connected(self) -> bool:
        """Ensure DBus connection is established."""
        if not self._connected:
            return await self._initialize_dbus()
        return self._connected
    
    async def get_devices(self) -> list[dict[str, Any]]:
        """Get list of network devices.
        
        Returns:
            List of device dictionaries with properties
        """
        if not await self._ensure_connected():
            return []
            
        try:
            # Get all devices
            devices_prop = self._nm_service.get_interface(
                "org.freedesktop.DBus.Properties"
            )
            
            devices = await devices_prop.Get(
                self.NM_SERVICE, 
                "Devices"
            )
            
            device_list = []
            for device_path in devices:
                device_info = await self._get_device_info(device_path)
                if device_info:
                    device_list.append(device_info)
                    
            return device_list
            
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Failed to get NetworkManager devices: {e}")
            else:
                logger.error(f"Failed to get NetworkManager devices: {e}")
            return []
    
    async def _get_device_info(self, device_path: str) -> dict[str, Any] | None:
        """Get detailed information about a device."""
        try:
            device_proxy = self._system_bus.get_proxy_object(
                self.NM_SERVICE,
                device_path,
                self.NM_DEVICE_INTERFACE
            )
            
            props = device_proxy.get_interface(
                "org.freedesktop.DBus.Properties"
            )
            
            # Get basic device properties
            device_type = await props.Get(
                self.NM_DEVICE_INTERFACE,
                "DeviceType"
            )
            
            interface = await props.Get(
                self.NM_DEVICE_INTERFACE,
                "Interface"
            )
            
            # Get MAC address
            try:
                mac_address = await props.Get(
                    self.NM_DEVICE_INTERFACE,
                    "HwAddress"
                )
            except dbus.exceptions.DBusException:
                mac_address = ""
            
            # Get state
            try:
                state = await props.Get(
                    self.NM_DEVICE_INTERFACE,
                    "State"
                )
            except dbus.exceptions.DBusException:
                state = 0  # Unknown
            
            # Get IP4 configuration if available
            ip4_config = {}
            try:
                ip4_path = await props.Get(
                    self.NM_DEVICE_INTERFACE,
                    "Ip4Config"
                )
                if ip4_path:
                    ip4_config = await self._get_ip_config(ip4_path)
            except dbus.exceptions.DBusException:
                pass
            
            # Get IP6 configuration if available
            ip6_config = {}
            try:
                ip6_path = await props.Get(
                    self.NM_DEVICE_INTERFACE,
                    "Ip6Config"
                )
                if ip6_path:
                    ip6_config = await self._get_ip_config(ip6_path)
            except dbus.exceptions.DBusException:
                pass
            
            # Get WiFi-specific properties if it's a WiFi device
            wifi_props = {}
            if device_type == 2:  # NM_DEVICE_TYPE_WIFI = 2
                try:
                    wifi_device = self._system_bus.get_proxy_object(
                        self.NM_SERVICE,
                        device_path,
                        self.NM_DEVICE_WIFI_INTERFACE
                    )
                    
                    wifi_props_obj = wifi_device.get_interface(
                        "org.freedesktop.DBus.Properties"
                    )
                    
                    # Get SSID
                    try:
                        ssid_bytes = await wifi_props_obj.Get(
                            self.NM_DEVICE_WIFI_INTERFACE,
                            "ActiveSsid"
                        )
                        # SSID is passed as array of bytes
                        if ssid_bytes:
                            ssid = ''.join(chr(b) for b in ssid_bytes)
                        else:
                            ssid = ""
                    except dbus.exceptions.DBusException:
                        ssid = ""
                    
                    # Get signal strength
                    try:
                        signal = await wifi_props_obj.Get(
                            self.NM_DEVICE_WIFI_INTERFACE,
                            "Strength"
                        )
                    except dbus.exceptions.DBusException:
                        signal = 0
                    
                    wifi_props = {
                        "ssid": ssid,
                        "signal": signal
                    }
                except dbus.exceptions.DBusException:
                    pass
            
            return {
                "path": device_path,
                "type": int(device_type),
                "interface": str(interface),
                "mac_address": str(mac_address),
                "state": int(state),
                "ipv4": ip4_config,
                "ipv6": ip6_config,
                "wifi": wifi_props
            }
            
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Failed to get device info for {device_path}: {e}")
            else:
                logger.error(f"Failed to get device info for {device_path}: {e}")
            return None
    
    async def _get_ip_config(self, config_path: str) -> dict[str, Any]:
        """Get IP configuration details."""
        try:
            ip_config = self._system_bus.get_proxy_object(
                self.NM_SERVICE,
                config_path,
                "org.freedesktop.NetworkManager.IP4Config"  # Simplified
            )
            
            props = ip_config.get_interface(
                "org.freedesktop.DBus.Properties"
            )
            
            # Get addresses
            addresses = []
            try:
                addr_arrays = await props.Get(
                    "org.freedesktop.NetworkManager.IP4Config",
                    "AddressData"
                )
                # Each address is a dict with 'address', 'prefix', etc.
                for addr_dict in addr_arrays:
                    addr = {
                        "address": str(addr_dict.get("address", "")),
                        "prefix": int(addr_dict.get("prefix", 0)),
                        "gateway": str(addr_dict.get("gateway", ""))
                    }
                    addresses.append(addr)
            except dbus.exceptions.DBusException:
                pass
            
            # Get DNS servers
            dns_servers = []
            try:
                dns_array = await props.Get(
                    "org.freedesktop.NetworkManager.IP4Config",
                    "DnsData"
                )
                for dns_dict in dns_array:
                    dns_servers.append(str(dns_dict.get("address", "")))
            except dbus.exceptions.DBusException:
                pass
            
            return {
                "addresses": addresses,
                "dns_servers": dns_servers
            }
            
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Failed to get IP config from {config_path}: {e}")
            else:
                logger.error(f"Failed to get IP config from {config_path}: {e}")
            return {"addresses": [], "dns_servers": []}
    
    async def get_connections(self) -> list[dict[str, Any]]:
        """Get list of network connections.
        
        Returns:
            List of connection dictionaries
        """
        if not await self._ensure_connected():
            return []
            
        try:
            # Get all connections from Settings service
            settings_props = self._nm_settings.get_interface(
                "org.freedesktop.DBus.Properties"
            )
            
            connections = await settings_props.Get(
                self.NM_SETTINGS_SERVICE,
                "Connections"
            )
            
            connection_list = []
            for connection_path in connections:
                conn_info = await self._get_connection_info(connection_path)
                if conn_info:
                    connection_list.append(conn_info)
                    
            return connection_list
            
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Failed to get NetworkManager connections: {e}")
            else:
                logger.error(f"Failed to get NetworkManager connections: {e}")
            return []
    
    async def _get_connection_info(self, connection_path: str) -> dict[str, Any] | None:
        """Get detailed information about a connection."""
        try:
            connection_proxy = self._system_bus.get_proxy_object(
                self.NM_SETTINGS_SERVICE,
                connection_path,
                self.NM_CONNECTION_INTERFACE
            )
            
            props = connection_proxy.get_interface(
                "org.freedesktop.DBus.Properties"
            )
            
            # Get connection settings
            settings = await props.Get(
                self.NM_CONNECTION_INTERFACE,
                "Settings"
            )
            
            # Extract useful information
            connection_info = {
                "path": connection_path,
                "id": "",
                "type": "",
                "uuid": "",
                "settings": settings
            }
            
            # Get connection ID from settings
            if "connection" in settings:
                conn_settings = settings["connection"]
                connection_info["id"] = str(conn_settings.get("id", ""))
                connection_info["type"] = str(conn_settings.get("type", ""))
                connection_info["uuid"] = str(conn_settings.get("uuid", ""))
            
            return connection_info
            
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Failed to get connection info for {connection_path}: {e}")
            else:
                logger.error(f"Failed to get connection info for {connection_path}: {e}")
            return None
    
    async def activate_connection(self, device_path: str, connection_path: str) -> bool:
        """Activate a connection on a device.
        
        Args:
            device_path: Device DBus path
            connection_path: Connection DBus path
            
        Returns:
            True if activation successful
        """
        if not await self._ensure_connected():
            return False
            
        try:
            # Call ActivateConnection method
            await self._nm_service.call_method(
                self.NM_INTERFACE,
                "ActivateConnection",
                "ssao",
                connection_path,
                device_path,
                "/",  # Specific object path (usually /)
                "[]"  # Empty options
            )
            
            if LOGURU_AVAILABLE:
                logger.info(f"Activated connection {connection_path} on device {device_path}")
            else:
                logger.info(f"Activated connection {connection_path} on device {device_path}")
            return True
            
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Failed to activate connection: {e}")
            else:
                logger.error(f"Failed to activate connection: {e}")
            return False
    
    async def deactivate_connection(self, device_path: str) -> bool:
        """Deactivate active connection on a device.
        
        Args:
            device_path: Device DBus path
            
        Returns:
            True if deactivation successful
        """
        if not await self._ensure_connected():
            return False
            
        try:
            # Get the active connection for this device
            device_proxy = self._system_bus.get_proxy_object(
                self.NM_SERVICE,
                device_path,
                self.NM_DEVICE_INTERFACE
            )
            
            props = device_proxy.get_interface(
                "org.freedesktop.DBus.Properties"
            )
            
            active_connection = await props.Get(
                self.NM_DEVICE_INTERFACE,
                "ActiveConnection"
            )
            
            if active_connection and str(active_connection) != "/":
                # Deactivate the connection
                await self._nm_service.call_method(
                    self.NM_INTERFACE,
                    "DeactivateConnection",
                    "o",
                    active_connection
                )
                
                if LOGURU_AVAILABLE:
                    logger.info(f"Deactivated connection on device {device_path}")
                else:
                    logger.info(f"Deactivated connection on device {device_path}")
                return True
            else:
                if LOGURU_AVAILABLE:
                    logger.debug(f"No active connection to deactivate on device {device_path}")
                else:
                    logger.debug(f"No active connection to deactivate on device {device_path}")
                return True  # Nothing to deactivate
                
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Failed to deactivate connection on device {device_path}: {e}")
            else:
                logger.error(f"Failed to deactivate connection on device {device_path}: {e}")
            return False
    
    async def add_connection(self, settings: dict[str, Any]) -> str | None:
        """Add a new network connection.
        
        Args:
            settings: Connection settings dictionary
            
        Returns:
            Connection path if successful, None otherwise
        """
        if not await self._ensure_connected():
            return None
            
        try:
            # Add connection via Settings service
            connection_path = await self._nm_settings.call_method(
                self.NM_SETTINGS_INTERFACE,
                "AddConnection",
                "a{sa{sv}}",
                settings
            )
            
            if LOGURU_AVAILABLE:
                logger.info(f"Added connection: {connection_path}")
            else:
                logger.info(f"Added connection: {connection_path}")
            return str(connection_path)
            
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Failed to add connection: {e}")
            else:
                logger.error(f"Failed to add connection: {e}")
            return None
    
    async def delete_connection(self, connection_path: str) -> bool:
        """Delete a network connection.
        
        Args:
            connection_path: Connection DBus path
            
        Returns:
            True if deletion successful
        """
        if not await self._ensure_connected():
            return False
            
        try:
            await self._nm_settings.call_method(
                self.NM_SETTINGS_INTERFACE,
                "RemoveConnection",
                "o",
                connection_path
            )
            
            if LOGURU_AVAILABLE:
                logger.info(f"Deleted connection: {connection_path}")
            else:
                logger.info(f"Deleted connection: {connection_path}")
            return True
            
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Failed to delete connection {connection_path}: {e}")
            else:
                logger.error(f"Failed to delete connection {connection_path}: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown DBus connection."""
        if self._system_bus:
            try:
                await self._system_bus.__aexit__(None, None, None)
            except Exception:
                pass  # Ignore errors during shutdown
            finally:
                self._system_bus = None
                self._nm_service = None
                self._nm_settings = None
                self._connected = False
                
                if LOGURU_AVAILABLE:
                    logger.info("NetworkManager DBus connection closed")
                else:
                    logger.info("NetworkManager DBus connection closed")


# Convenience function to get a NetworkManager backend instance
async def get_network_manager() -> NetworkManagerBackend:
    """Get initialized NetworkManager backend.
    
    Returns:
        NetworkManagerBackend instance
        
    Raises:
        RuntimeError: If NetworkManager DBus is not available
    """
    nm = NetworkManagerBackend()
    if not await nm._initialize_dbus():
        raise RuntimeError("Failed to initialize NetworkManager DBus")
    return nm


__all__ = [
    "NetworkManagerBackend",
    "get_network_manager"
]