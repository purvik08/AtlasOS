"""wpa_supplicant DBus integration for Atlas OS."""

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

# Check if we're on Linux (wpa_supplicant is Linux-specific)
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


class WpaSupplicantBackend:
    """Async wrapper for wpa_supplicant DBus API (fi.w1.wpa_supplicant1)."""
    
    # wpa_supplicant DBus constants
    WPAS_SERVICE = "fi.w1.wpa_supplicant1"
    WPAS_PATH = "/fi/w1/wpa_supplicant1"
    WPAS_INTERFACE = "fi.w1.wpa_supplicant1"
    
    # Interface interfaces
    WPAS_INTERFACE_INTERFACE = "fi.w1.wpa_supplicant1.Interface"
    
    # BSS (access point) interface
    WPAS_BSS_INTERFACE = "fi.w1.wpa_supplicant1.BSS"
    
    def __init__(self) -> None:
        """Initialize wpa_supplicant backend."""
        self._system_bus = None
        self._wpas_service = None
        self._interfaces = {}  # Cache of interface objects
        self._connected = False
        
    async def _initialize_dbus(self) -> bool:
        """Initialize DBus connection."""
        if not _IS_LINUX:
            if LOGURU_AVAILABLE:
                logger.warning("wpa_supplicant DBus only available on Linux")
            else:
                logger.warning("wpa_supplicant DBus only available on Linux")
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
            
            # Get wpa_supplicant service
            self._wpas_service = self._system_bus.get_proxy_object(
                self.WPAS_SERVICE,
                self.WPAS_PATH,
                self.WPAS_INTERFACE
            )
            
            self._connected = True
            if LOGURU_AVAILABLE:
                logger.info("wpa_supplicant DBus connection established")
            else:
                logger.info("wpa_supplicant DBus connection established")
            return True
            
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Failed to initialize wpa_supplicant DBus: {e}")
            else:
                logger.error(f"Failed to initialize wpa_supplicant DBus: {e}")
            return False
    
    async def _ensure_connected(self) -> bool:
        """Ensure DBus connection is established."""
        if not self._connected:
            return await self._initialize_dbus()
        return self._connected
    
    async def get_interfaces(self) -> list[dict[str, Any]]:
        """Get list of wireless interfaces.
        
        Returns:
            List of interface dictionaries with properties
        """
        if not await self._ensure_connected():
            return []
            
        try:
            # Get all interfaces
            interfaces_prop = self._wpas_service.get_interface(
                "org.freedesktop.DBus.Properties"
            )
            
            interfaces = await interfaces_prop.Get(
                self.WPAS_SERVICE,
                "Interfaces"
            )
            
            interface_list = []
            for iface_path in interfaces:
                iface_info = await self._get_interface_info(iface_path)
                if iface_info:
                    interface_list.append(iface_info)
                    # Cache the interface object for later use
                    self._interfaces[iface_path] = iface_info
                    
            return interface_list
            
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Failed to get wpa_supplicant interfaces: {e}")
            else:
                logger.error(f"Failed to get wpa_supplicant interfaces: {e}")
            return []
    
    async def _get_interface_info(self, iface_path: str) -> dict[str, Any] | None:
        """Get detailed information about a wireless interface."""
        try:
            iface_proxy = self._system_bus.get_proxy_object(
                self.WPAS_SERVICE,
                iface_path,
                self.WPAS_INTERFACE_INTERFACE
            )
            
            props = iface_proxy.get_interface(
                "org.freedesktop.DBus.Properties"
            )
            
            # Get interface properties
            ifname = await props.Get(
                self.WPAS_INTERFACE_INTERFACE,
                "Ifname"
            )
            
            # Get MAC address
            try:
                mac_address = await props.Get(
                    self.WPAS_INTERFACE_INTERFACE,
                    "MacAddress"
                )
            except dbus.exceptions.DBusException:
                mac_address = ""
            
            # Get state
            try:
                state = await props.Get(
                    self.WPAS_INTERFACE_INTERFACE,
                    "State"
                )
            except dbus.exceptions.DBusException:
                state = "disconnected"  # Default state
            
            # Get current AP (if connected)
            current_ap = "/"
            try:
                current_ap = await props.Get(
                    self.WPAS_INTERFACE_INTERFACE,
                    "CurrentBSS"
                )
            except dbus.exceptions.DBusException:
                pass
            
            # Get available networks (if in scanning state or idle)
            networks = []
            try:
                # Only attempt to get networks if we're not actively connected/scanning
                # This is a simplification - in reality we'd need to handle state properly
                if str(state) in ["disconnected", "inactive", "scanning"]:
                    networks = await self._get_available_networks(iface_path)
            except Exception:
                # If we can't get networks, continue with empty list
                pass
            
            return {
                "path": iface_path,
                "ifname": str(ifname),
                "mac_address": str(mac_address),
                "state": str(state),
                "current_ap": str(current_ap),
                "networks": networks
            }
            
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Failed to get interface info for {iface_path}: {e}")
            else:
                logger.error(f"Failed to get interface info for {iface_path}: {e}")
            return None
    
    async def _get_available_networks(self, iface_path: str) -> list[dict[str, Any]]:
        """Get available networks from scan results."""
        try:
            iface_proxy = self._system_bus.get_proxy_object(
                self.WPAS_SERVICE,
                iface_path,
                self.WPAS_INTERFACE_INTERFACE
            )
            
            props = iface_proxy.get_interface(
                "org.freedesktop.DBus.Properties"
            )
            
            # Get scan results
            try:
                bss_array = await props.Get(
                    self.WPAS_INTERFACE_INTERFACE,
                    "ScanResults"
                )
                
                networks = []
                for bss_path in bss_array:
                    bss_info = await self._get_bss_info(bss_path)
                    if bss_info:
                        networks.append(bss_info)
                
                return networks
            except dbus.exceptions.DBusException:
                # No scan results available
                return []
                
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Failed to get available networks for {iface_path}: {e}")
            else:
                logger.error(f"Failed to get available networks for {iface_path}: {e}")
            return []
    
    async def _get_bss_info(self, bss_path: str) -> dict[str, Any] | None:
        """Get information about a BSS (access point) from scan results."""
        try:
            bss_proxy = self._system_bus.get_proxy_object(
                self.WPAS_SERVICE,
                bss_path,
                self.WPAS_BSS_INTERFACE
            )
            
            props = bss_proxy.get_interface(
                "org.freedesktop.DBus.Properties"
            )
            
            # Get BSSID (MAC address)
            try:
                bssid = await props.Get(
                    self.WPAS_BSS_INTERFACE,
                    "BSSID"
                )
            except dbus.exceptions.DBusException:
                bssid = []
            
            # Get SSID
            try:
                ssid_bytes = await props.Get(
                    self.WPAS_BSS_INTERFACE,
                    "SSID"
                )
                # SSID is passed as array of bytes
                if ssid_bytes:
                    ssid = ''.join(chr(b) for b in ssid_bytes)
                else:
                    ssid = ""
            except dbus.exceptions.DBusException:
                ssid = ""
            
            # Get frequency (in MHz)
            try:
                frequency = await props.Get(
                    self.WPAS_BSS_INTERFACE,
                    "Frequency"
                )
            except dbus.exceptions.DBusException:
                frequency = 0
            
            # Get signal strength (in dBm)
            try:
                signal = await props.Get(
                    self.WPAS_BSS_INTERFACE,
                    "Signal"
                )
            except dbus.exceptions.DBusException:
                signal = 0
            
            # Get capabilities (encryption, etc.)
            try:
                flags = await props.Get(
                    self.WPAS_BSS_INTERFACE,
                    "Flags"
                )
            except dbus.exceptions.DBusException:
                flags = []
            
            # Get RSN IE (WPA2) if available
            try:
                rsn_ie = await props.Get(
                    self.WPAS_BSS_INTERFACE,
                    "RSN"
                )
                has_wpa2 = len(rsn_ie) > 0 if isinstance(rsn_ie, bytes) else False
            except dbus.exceptions.DBusException:
                has_wpa2 = False
            
            # Get WPA IE if available
            try:
                wpa_ie = await props.Get(
                    self.WPAS_BSS_INTERFACE,
                    "WPA"
                )
                has_wpa = len(wpa_ie) > 0 if isinstance(wpa_ie, bytes) else False
            except dbus.exceptions.DBusException:
                has_wpa = False
            
            return {
                "path": bss_path,
                "bssid": ':'.join(f'{b:02x}' for b in bssid) if isinstance(bssid, (list, tuple)) else str(bssid),
                "ssid": ssid,
                "frequency": int(frequency),
                "signal": int(signal),
                "flags": list(flags) if hasattr(flags, '__iter__') else [],
                "has_wpa2": bool(has_wpa2),
                "has_wpa": bool(has_wpa)
            }
            
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Failed to get BSS info for {bss_path}: {e}")
            else:
                logger.error(f"Failed to get BSS info for {bss_path}: {e}")
            return None
    
    async def scan(self, iface_name: str) -> bool:
        """Request a scan on a wireless interface.
        
        Args:
            iface_name: Interface name (e.g., "wlan0")
            
        Returns:
            True if scan requested successfully
        """
        if not await self._ensure_connected():
            return False
            
        try:
            # Find the interface path by ifname
            iface_path = await self._get_interface_path_by_ifname(iface_name)
            if not iface_path:
                if LOGURU_AVAILABLE:
                    logger.error(f"Interface {iface_name} not found")
                else:
                    logger.error(f"Interface {iface_name} not found")
                return False
            
            # Trigger scan
            iface_proxy = self._system_bus.get_proxy_object(
                self.WPAS_SERVICE,
                iface_path,
                self.WPAS_INTERFACE_INTERFACE
            )
            
            await iface_proxy.call_method(
                self.WPAS_INTERFACE_INTERFACE,
                "Scan",
                "a{sv}",
                {}  # Empty arguments
            )
            
            if LOGURU_AVAILABLE:
                logger.debug(f"Scan requested on interface {iface_name}")
            else:
                logger.debug(f"Scan requested on interface {iface_name}")
            return True
            
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Failed to request scan on interface {iface_name}: {e}")
            else:
                logger.error(f"Failed to request scan on interface {iface_name}: {e}")
            return False
    
    async def get_scan_results(self, iface_name: str) -> list[dict[str, Any]]:
        """Get scan results for a wireless interface.
        
        Args:
            iface_name: Interface name (e.g., "wlan0")
            
        Returns:
            List of discovered networks from scan results
        """
        if not await self._ensure_connected():
            return []
            
        try:
            # Find the interface path by ifname
            iface_path = await self._get_interface_path_by_ifname(iface_name)
            if not iface_path:
                if LOGURU_AVAILABLE:
                    logger.error(f"Interface {iface_name} not found")
                else:
                    logger.error(f"Interface {iface_name} not found")
                return []
            
            # Get interface info which includes cached scan results
            iface_info = await self._get_interface_info(iface_path)
            if iface_info:
                return iface_info.get("networks", [])
            else:
                return []
                
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Failed to get scan results for interface {iface_name}: {e}")
            else:
                logger.error(f"Failed to get scan results for interface {iface_name}: {e}")
            return []
    
    async def _get_interface_path_by_ifname(self, ifname: str) -> str | None:
        """Find interface DBus path by interface name."""
        try:
            interfaces = await self.get_interfaces()
            for iface in interfaces:
                if iface.get("ifname") == ifname:
                    return iface.get("path")
            return None
        except Exception:
            return None
    
    async def add_network(self, iface_name: str, ssid: str, psk: str | None = None) -> str | None:
        """Add a network to a wireless interface.
        
        Args:
            iface_name: Interface name (e.g., "wlan0")
            ssid: Network SSID
            psk: Pre-shared key (password) for WPA-PSK networks
            
        Returns:
            Network object path if successful, None otherwise
        """
        if not await self._ensure_connected():
            return None
            
        try:
            # Find the interface path by ifname
            iface_path = await self._get_interface_path_by_ifname(iface_name)
            if not iface_path:
                if LOGURU_AVAILABLE:
                    logger.error(f"Interface {iface_name} not found")
                else:
                    logger.error(f"Interface {iface_name} not found")
                return None
            
            # Get the interface object
            iface_proxy = self._system_bus.get_proxy_object(
                self.WPAS_SERVICE,
                iface_path,
                self.WPAS_INTERFACE_INTERFACE
            )
            
            # Prepare network properties
            props = {}
            props["ssid"] = dbus.Array([dbus.Byte(c.encode('utf-8')[0]) for c in ssid], signature='y')
            
            if psk is not None:
                # For WPA-PSK, we need to provide the PSK
                # wpa_supplicant expects the PSK as either:
                # 1. A 64-character hexadecimal string (for pre-hashed PSK)
                # 2. An ASCII passphrase (8-63 characters)
                # We'll assume it's a passphrase and let wpa_supplicant handle the hashing
                if len(psk) >= 8 and len(psk) <= 63:
                    props["psk"] = dbus.String(psk)
                elif len(psk) == 64:  # Assume it's already a hex PSK
                    # Convert hex string to bytes
                    try:
                        psk_bytes = bytes.fromhex(psk)
                        props["psk"] = dbus.Array([dbus.Byte(b) for b in psk_bytes], signature='y')
                    except ValueError:
                        # If not valid hex, treat as passphrase anyway
                        props["psk"] = dbus.String(psk)
                else:
                    # Invalid length, but try anyway
                    props["psk"] = dbus.String(psk)
            
            # Add the network
            network_path = await iface_proxy.call_method(
                self.WPAS_INTERFACE_INTERFACE,
                "AddNetwork",
                "a{sv}",
                props
            )
            
            if LOGURU_AVAILABLE:
                logger.info(f"Added network '{ssid}' to interface {iface_name}: {network_path}")
            else:
                logger.info(f"Added network '{ssid}' to interface {iface_name}: {network_path}")
            return str(network_path)
            
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Failed to add network to interface {iface_name}: {e}")
            else:
                logger.error(f"Failed to add network to interface {iface_name}: {e}")
            return None
    
    async def select_network(self, iface_name: str, network_path: str) -> bool:
        """Select a network for association.
        
        Args:
            iface_name: Interface name (e.g., "wlan0")
            network_path: Network object DBus path
            
        Returns:
            True if network selected successfully
        """
        if not await self._ensure_connected():
            return False
            
        try:
            # Find the interface path by ifname
            iface_path = await self._get_interface_path_by_ifname(iface_name)
            if not iface_path:
                if LOGURU_AVAILABLE:
                    logger.error(f"Interface {iface_name} not found")
                else:
                    logger.error(f"Interface {iface_name} not found")
                return False
            
            # Get the interface object
            iface_proxy = self._system_bus.get_proxy_object(
                self.WPAS_SERVICE,
                iface_path,
                self.WPAS_INTERFACE_INTERFACE
            )
            
            # Select the network
            await iface_proxy.call_method(
                self.WPAS_INTERFACE_INTERFACE,
                "SelectNetwork",
                "o",
                network_path
            )
            
            if LOGURU_AVAILABLE:
                logger.info(f"Selected network {network_path} on interface {iface_name}")
            else:
                logger.info(f"Selected network {network_path} on interface {iface_name}")
            return True
            
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Failed to select network on interface {iface_name}: {e}")
            else:
                logger.error(f"Failed to select network on interface {iface_name}: {e}")
            return False
    
    async def enable_network(self, iface_name: str, network_path: str) -> bool:
        """Enable a selected network for association.
        
        Args:
            iface_name: Interface name (e.g., "wlan0")
            network_path: Network object DBus path
            
        Returns:
            True if network enabled successfully
        """
        if not await self._ensure_connected():
            return False
            
        try:
            # Find the interface path by ifname
            iface_path = await self._get_interface_path_by_ifname(iface_name)
            if not iface_path:
                if LOGURU_AVAILABLE:
                    logger.error(f"Interface {iface_name} not found")
                else:
                    logger.error(f"Interface {iface_name} not found")
                return False
            
            # Get the interface object
            iface_proxy = self._system_bus.get_proxy_object(
                self.WPAS_SERVICE,
                iface_path,
                self.WPAS_INTERFACE_INTERFACE
            )
            
            # Enable the network
            await iface_proxy.call_method(
                self.WPAS_INTERFACE_INTERFACE,
                "EnableNetwork",
                "o",
                network_path
            )
            
            if LOGURU_AVAILABLE:
                logger.info(f"Enabled network {network_path} on interface {iface_name}")
            else:
                logger.info(f"Enabled network {network_path} on interface {iface_name}")
            return True
            
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Failed to enable network on interface {iface_name}: {e}")
            else:
                logger.error(f"Failed to enable network on interface {iface_name}: {e}")
            return False
    
    async def disconnect(self, iface_name: str) -> bool:
        """Disconnect from current network.
        
        Args:
            iface_name: Interface name (e.g., "wlan0")
            
        Returns:
            True if disconnection successful
        """
        if not await self._ensure_connected():
            return False
            
        try:
            # Find the interface path by ifname
            iface_path = await self._get_interface_path_by_ifname(iface_name)
            if not iface_path:
                if LOGURU_AVAILABLE:
                    logger.error(f"Interface {iface_name} not found")
                else:
                    logger.error(f"Interface {iface_name} not found")
                return False
            
            # Get the interface object
            iface_proxy = self._system_bus.get_proxy_object(
                self.WPAS_SERVICE,
                iface_path,
                self.WPAS_INTERFACE_INTERFACE
            )
            
            # Disconnect
            await iface_proxy.call_method(
                self.WPAS_INTERFACE_INTERFACE,
                "Disconnect",
                ""
            )
            
            if LOGURU_AVAILABLE:
                logger.info(f"Disconnected interface {iface_name}")
            else:
                logger.info(f"Disconnected interface {iface_name}")
            return True
            
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Failed to disconnect interface {iface_name}: {e}")
            else:
                logger.error(f"Failed to disconnect interface {iface_name}: {e}")
            return False
    
    async def delete_network(self, iface_name: str, network_path: str) -> bool:
        """Delete a network from a wireless interface.
        
        Args:
            iface_name: Interface name (e.g., "wlan0")
            network_path: Network object DBus path
            
        Returns:
            True if network deleted successfully
        """
        try:
            # Find the interface path by ifname
            iface_path = await self._get_interface_path_by_ifname(iface_name)
            if not iface_path:
                if LOGURU_AVAILABLE:
                    logger.error(f"Interface {iface_name} not found")
                else:
                    logger.error(f"Interface {iface_name} not found")
                return False
            
            # Get the interface object
            iface_proxy = self._system_bus.get_proxy_object(
                self.WPAS_SERVICE,
                iface_path,
                self.WPAS_INTERFACE_INTERFACE
            )
            
            # Remove the network
            await iface_proxy.call_method(
                self.WPAS_INTERFACE_INTERFACE,
                "RemoveNetwork",
                "o",
                network_path
            )
            
            if LOGURU_AVAILABLE:
                logger.info(f"Removed network {network_path} from interface {iface_name}")
            else:
                logger.info(f"Removed network {network_path} from interface {iface_name}")
            return True
            
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Failed to remove network from interface {iface_name}: {e}")
            else:
                logger.error(f"Failed to remove network from interface {iface_name}: {e}")
            return False
    
    async def _get_interface_info_by_ifname(self, ifname: str) -> dict[str, Any] | None:
        """Get interface information by interface name."""
        try:
            interfaces = await self.get_interfaces()
            for iface in interfaces:
                if iface.get("ifname") == ifname:
                    return iface
            return None
        except Exception:
            return None
    
    async def shutdown(self) -> None:
        """Shutdown DBus connection."""
        if self._system_bus:
            try:
                await self._system_bus.__aexit__(None, None, None)
            except Exception:
                pass  # Ignore errors during shutdown
            finally:
                self._system_bus = None
                self._wpas_service = None
                self._interfaces.clear()
                self._connected = False
                
                if LOGURU_AVAILABLE:
                    logger.info("wpa_supplicant DBus connection closed")
                else:
                    logger.info("wpa_supplicant DBus connection closed")


# Convenience function to get a wpa_supplicant backend instance
async def get_wpa_supplicant() -> WpaSupplicantBackend:
    """Get initialized wpa_supplicant backend.
    
    Returns:
        WpaSupplicantBackend instance
        
    Raises:
        RuntimeError: If wpa_supplicant DBus is not available
    """
    wpas = WpaSupplicantBackend()
    if not await wpas._initialize_dbus():
        raise RuntimeError("Failed to initialize wpa_supplicant DBus")
    return wpas


__all__ = [
    "WpaSupplicantBackend",
    "get_wpa_supplicant"
]