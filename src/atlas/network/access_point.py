"""Access Point management for Atlas OS."""

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

# Import our NetworkManager backend
from .nm import get_network_manager


class AccessPointManager:
    """Manages Access Point (hotspot) functionality using NetworkManager."""

    def __init__(self) -> None:
        self._is_active = False
        self._ssid: str | None = None
        self._nm_backend: Any = None  # Will be NetworkManagerBackend
        self._initialized = False

    async def _ensure_backend(self) -> bool:
        """Initialize NetworkManager backend if needed."""
        if self._initialized:
            return True
            
        try:
            # Initialize NetworkManager backend
            self._nm_backend = await get_network_manager()
            
            self._initialized = True
            if LOGURU_AVAILABLE:
                logger.debug("AccessPointManager backend initialized")
            else:
                logger.debug("AccessPointManager backend initialized")
            return True
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Failed to initialize AccessPointManager backend: {e}")
            else:
                logger.error(f"Failed to initialize AccessPointManager backend: {e}")
            return False

    async def start_ap(
        self,
        ssid: str,
        password: str = "",
        channel: int = 6,
        security: str = "WPA2",
        interface: str | None = None
    ) -> bool:
        """Start Access Point (hotspot) using NetworkManager.

        Args:
            ssid: Network SSID for the AP
            password: Network password (empty for open network)
            channel: WiFi channel (1-13)
            security: Security type (WPA2, WPA3, WEP, None)
            interface: Specific interface to use (None for default)

        Returns:
            True if AP started successfully, False otherwise

        """
        if self._is_active:
            if LOGURU_AVAILABLE:
                logger.warning("Access Point already active")
            else:
                logger.warning("Access Point already active")
            return False

        try:
            if not await self._ensure_backend():
                if LOGURU_AVAILABLE:
                    logger.error("Failed to initialize NetworkManager backend")
                else:
                    logger.error("Failed to initialize NetworkManager backend")
                return False

            system = platform.system().lower()

            if system == "linux":
                success = await self._start_ap_linux_nm(
                    ssid, password, channel, security, interface
                )
            elif system == "windows":
                success = await self._start_ap_windows(
                    ssid, password, channel, security, interface
                )
            elif system == "darwin":
                success = await self._start_ap_macos(
                    ssid, password, channel, security, interface
                )
            else:
                if LOGURU_AVAILABLE:
                    logger.error(f"Unsupported platform: {system}")
                else:
                    logger.error(f"Unsupported platform: {system}")
                success = False

            if success:
                self._is_active = True
                self._ssid = ssid
                if LOGURU_AVAILABLE:
                    logger.info(f"Started Access Point: {ssid}")
                else:
                    logger.info(f"Started Access Point: {ssid}")
            else:
                if LOGURU_AVAILABLE:
                    logger.error(f"Failed to start Access Point: {ssid}")
                else:
                    logger.error(f"Failed to start Access Point: {ssid}")

            return success

        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Error starting Access Point {ssid}: {e}")
            else:
                logger.error(f"Error starting Access Point {ssid}: {e}")
            return False

    async def stop_ap(self, interface: str | None = None) -> bool:
        """Stop Access Point (hotspot).

        Args:
            interface: Specific interface to use (None for default)

        Returns:
            True if AP stopped successfully, False otherwise

        """
        if not self._is_active:
            if LOGURU_AVAILABLE:
                logger.warning("Access Point not active")
            else:
                logger.warning("Access Point not active")
            return True

        try:
            if not await self._ensure_backend():
                if LOGURU_AVAILABLE:
                    logger.error("Failed to initialize NetworkManager backend")
                else:
                    logger.error("Failed to initialize NetworkManager backend")
                return False

            system = platform.system().lower()

            if system == "linux":
                success = await self._stop_ap_linux_nm(interface)
            elif system == "windows":
                success = await self._stop_ap_windows(interface)
            elif system == "darwin":
                success = await self._stop_ap_macos(interface)
            else:
                if LOGURU_AVAILABLE:
                    logger.error(f"Unsupported platform: {system}")
                else:
                    logger.error(f"Unsupported platform: {system}")
                success = False

            if success:
                self._is_active = False
                self._ssid = None
                if LOGURU_AVAILABLE:
                    logger.info("Stopped Access Point")
                else:
                    logger.info("Stopped Access Point")
            else:
                if LOGURU_AVAILABLE:
                    logger.error("Failed to stop Access Point")
                else:
                    logger.error("Failed to stop Access Point")

            return success

        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Error stopping Access Point: {e}")
            else:
                logger.error(f"Error stopping Access Point: {e}")
            return False

    @property
    def is_active(self) -> bool:
        """Check if Access Point is currently active."""
        return self._is_active

    @property
    def ssid(self) -> str | None:
        """Get the SSID of the active Access Point."""
        return self._ssid

    # Platform-specific implementation methods using NetworkManager
    async def _start_ap_linux_nm(
        self,
        ssid: str,
        password: str,
        channel: int,
        security: str,
        interface: str | None
    ) -> bool:
        """Start Access Point on Linux using NetworkManager."""
        try:
            # Determine interface to use
            if interface is None:
                # Get available interfaces and pick a suitable wireless one
                devices = await self._nm_backend.get_devices()
                wifi_devices = [
                    device for device in devices 
                    if device.get("type") == 2  # NM_DEVICE_TYPE_WIFI = 2
                ]
                if not wifi_devices:
                    if LOGURU_AVAILABLE:
                        logger.error("No wireless interfaces found for AP")
                    else:
                        logger.error("No wireless interfaces found for AP")
                    return False
                interface = wifi_devices[0]["interface"]
            
            # Find the device path for this interface
            devices = await self._nm_backend.get_devices()
            device_path = None
            for device in devices:
                if device.get("interface") == interface:
                    device_path = device.get("path")
                    break
            
            if not device_path:
                if LOGURU_AVAILABLE:
                    logger.error(f"No NetworkManager device found for interface {interface}")
                else:
                    logger.error(f"No NetworkManager device found for interface {interface}")
                return False
            
            # Create AP connection settings
            # This is a simplified implementation - in reality we'd need to create
            # proper 802-11-wireless, 802-11-wireless-security, ipv4, and connection settings
            ap_settings = {
                "connection": {
                    "id": f"Atlas-AP-{ssid}",
                    "type": "802-11-wireless",
                    "autoconnect": False,
                    "interface_name": interface
                },
                "802-11-wireless": {
                    "ssid": ssid.encode('utf-8'),  # SSID as bytes
                    "mode": "ap",
                    "band": "bg",  # Could be made configurable based on channel
                    "channel": channel
                },
                "802-11-wireless-security": {},
                "ipv4": {
                    "method": "shared"  # Shared AP mode (provides NAT and DHCP)
                },
                "ipv6": {
                    "method": "ignore"
                }
            }
            
            # Configure security based on the security parameter
            if security.upper() == "WPA2" and password:
                ap_settings["802-11-wireless-security"] = {
                    "key-mgmt": "wpa-psk",
                    "psk": password
                }
            elif security.upper() == "WEP" and password:
                # WEP keys are more complex - for simplicity we'll skip WEP for now
                if LOGURU_AVAILABLE:
                    logger.warning("WEP security not fully implemented for AP")
                else:
                    logger.warning("WEP security not fully implemented for AP")
                return False
            elif security.upper() == "WPA3" and password:
                # WPA3 support depends on NetworkManager/wpa_supplicant version
                if LOGURU_AVAILABLE:
                    logger.warning("WPA3 security may not be fully supported")
                else:
                    logger.warning("WPA3 security may not be fully supported")
                # Try WPA2 as fallback
                ap_settings["802-11-wireless-security"] = {
                    "key-mgmt": "wpa-psk",
                    "psk": password
                }
            elif security.upper() == "NONE" or not password:
                # Open network - no security settings needed
                pass
            else:
                if LOGURU_AVAILABLE:
                    logger.error(f"Unsupported security type: {security}")
                else:
                    logger.error(f"Unsupported security type: {security}")
                return False
            
            # Add the connection via NetworkManager
            connection_path = await self._nm_backend.add_connection(ap_settings)
            if not connection_path:
                if LOGURU_AVAILABLE:
                    logger.error(f"Failed to add AP connection for {ssid}")
                else:
                    logger.error(f"Failed to add AP connection for {ssid}")
                return False
            
            # Activate the connection (this will start the AP)
            success = await self._nm_backend.activate_connection(device_path, connection_path)
            if not success:
                if LOGURU_AVAILABLE:
                    logger.error(f"Failed to activate AP connection for {ssid}")
                else:
                    logger.error(f"Failed to activate AP connection for {ssid}")
                # Clean up: remove the connection we just added
                await self._nm_backend.delete_connection(connection_path)
                return False
            
            # Wait a bit for AP to start
            await asyncio.sleep(3.0)
            
            # Verify the AP is active by checking if the connection is activated
            # In a full implementation, we'd monitor the connection state
            if LOGURU_AVAILABLE:
                logger.info(f"Started Access Point: {ssid} on interface {interface} via NetworkManager")
            else:
                logger.info(f"Started Access Point: {ssid} on interface {interface} via NetworkManager")
            return True
            
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Error starting Access Point on Linux via NetworkManager: {e}")
            else:
                logger.error(f"Error starting Access Point on Linux via NetworkManager: {e}")
            return False

    async def _start_ap_windows(
        self,
        ssid: str,
        password: str,
        channel: int,
        security: str,
        interface: str | None
    ) -> bool:
        """Start Access Point on Windows using netsh."""
        try:
            logger.warning("Access Point on Windows not fully implemented")
            return False
        except Exception as e:
            logger.error(f"Error starting Access Point on Windows: {e}")
            return False

    async def _start_ap_macos(
        self,
        ssid: str,
        password: str,
        channel: int,
        security: str,
        interface: str | None
    ) -> bool:
        """Start Access Point on macOS."""
        try:
            logger.warning("Access Point on macOS not fully implemented")
            return False
        except Exception as e:
            logger.error(f"Error starting Access Point on macOS: {e}")
            return False

    async def _stop_ap_linux_nm(self, interface: str | None) -> bool:
        """Stop Access Point on Linux using NetworkManager."""
        try:
            # Determine interface to use
            if interface is None:
                # For stopping, we need to find the active AP interface
                # This is simplified - in reality we'd track which interface we started AP on
                devices = await self._nm_backend.get_devices()
                wifi_devices = [
                    device for device in devices 
                    if device.get("type") == 2  # NM_DEVICE_TYPE_WIFI = 2
                ]
                if not wifi_devices:
                    if LOGURU_AVAILABLE:
                        logger.warning("No wireless interfaces found")
                    else:
                        logger.warning("No wireless interfaces found")
                    return True  # Nothing to stop
                # Use the first wireless interface (in practice we'd track the specific one)
                interface = wifi_devices[0]["interface"]
            
            # Find the device path for this interface
            devices = await self._nm_backend.get_devices()
            device_path = None
            for device in devices:
                if device.get("interface") == interface:
                    device_path = device.get("path")
                    break
            
            if not device_path:
                if LOGURU_AVAILABLE:
                    logger.warning(f"No NetworkManager device found for interface {interface}")
                else:
                    logger.warning(f"No NetworkManager device found for interface {interface}")
                return True  # Nothing to stop if we can't find the device
            
            # Deactivate any active connection on this device (this should stop the AP)
            success = await self._nm_backend.deactivate_connection(device_path)
            if not success:
                if LOGURU_AVAILABLE:
                    logger.error(f"Failed to deactivate connection on interface {interface}")
                else:
                    logger.error(f"Failed to deactivate connection on interface {interface}")
                return False
            
            # Wait a bit for AP to stop
            await asyncio.sleep(2.0)
            
            if LOGURU_AVAILABLE:
                logger.info(f"Stopped Access Point on interface {interface} via NetworkManager")
            else:
                logger.info(f"Stopped Access Point on interface {interface} via NetworkManager")
            return True
            
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Error stopping Access Point on Linux via NetworkManager: {e}")
            else:
                logger.error(f"Error stopping Access Point on Linux via NetworkManager: {e}")
            return False

    async def _stop_ap_windows(self, interface: str | None) -> bool:
        """Stop Access Point on Windows."""
        try:
            logger.warning("Access Point stop on Windows not fully implemented")
            return False
        except Exception as e:
            logger.error(f"Error stopping Access Point on Windows: {e}")
            return False

    async def _stop_ap_macos(self, interface: str | None) -> bool:
        """Stop Access Point on macOS."""
        try:
            logger.warning("Access Point stop on macOS not fully implemented")
            return False
        except Exception as e:
            logger.error(f"Error stopping Access Point on macOS: {e}")
            return False

    async def shutdown(self) -> None:
        """Shutdown the Access Point manager and release resources."""
        try:
            if self._nm_backend:
                await self._nm_backend.shutdown()
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Error shutting down AccessPointManager: {e}")
            else:
                logger.error(f"Error shutting down AccessPointManager: {e}")
        finally:
            self._nm_backend = None
            self._initialized = False


__all__ = [
    "AccessPointManager"
]