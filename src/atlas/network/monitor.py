"""Network monitoring and health checks for Atlas OS."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

# Optional import for loguru
try:
    from loguru import logger
    LOGURU_AVAILABLE = True
except ImportError:
    LOGURU_AVAILABLE = False
    import logging
    logger = logging.getLogger(__name__)

# Import types for type checking to avoid circular imports
if TYPE_CHECKING:
    from .__init__ import NetworkInterface, WifiNetwork

# Import from our own network module (for functions)
from atlas.network.access_point import AccessPointManager
from atlas.network.mdns import MDNSService
from atlas.network.wifi import WiFiManager


class NetworkMonitor:
    """Monitors network connectivity and provides health information."""

    def __init__(self) -> None:
        self._wifi_manager = WiFiManager()
        self._ap_manager = AccessPointManager()
        self._mdns_service = MDNSService()
        self._last_check_time: float = 0.0
        self._check_interval: float = 30.0  # seconds
        self._is_initialized = False

    async def initialize(self) -> bool:
        """Initialize network monitoring components.

        Returns:
            True if initialized successfully, False otherwise

        """
        if self._is_initialized:
            if LOGURU_AVAILABLE:
                logger.warning("Network monitor already initialized")
            else:
                logger.warning("Network monitor already initialized")
            return True

        try:
            # Start mDNS service if enabled
            # This would come from configuration in a real implementation
            # await self._mdns_service.start()

            self._is_initialized = True
            if LOGURU_AVAILABLE:
                logger.info("Network monitor initialized")
            else:
                logger.info("Network monitor initialized")
            return True
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Failed to initialize network monitor: {e}")
            else:
                logger.error(f"Failed to initialize network monitor: {e}")
            return False

    async def shutdown(self) -> bool:
        """Shutdown network monitoring components.

        Returns:
            True if shutdown successful, False otherwise

        """
        if not self._is_initialized:
            if LOGURU_AVAILABLE:
                logger.warning("Network monitor not initialized")
            else:
                logger.warning("Network monitor not initialized")
            return True

        try:
            # Stop mDNS service
            # await self._mdns_service.stop()

            self._is_initialized = False
            if LOGURU_AVAILABLE:
                logger.info("Network monitor shutdown")
            else:
                logger.info("Network monitor shutdown")
            return True
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Error shutting down network monitor: {e}")
            else:
                logger.error(f"Error shutting down network monitor: {e}")
            return False

    async def get_network_interfaces(self) -> list[NetworkInterface]:
        """Get all network interfaces with their details.

        Returns:
            List of network interfaces

        """
        # Delegate to existing function for backward compatibility
        try:
            from atlas.network import get_network_interfaces

            interfaces = await get_network_interfaces()
            if LOGURU_AVAILABLE:
                logger.debug(f"Retrieved {len(interfaces)} network interfaces")
            else:
                logger.debug(f"Retrieved {len(interfaces)} network interfaces")
            return interfaces
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Error getting network interfaces: {e}")
            else:
                logger.error(f"Error getting network interfaces: {e}")
            return []

    async def scan_wifi_networks(self, interface: str | None = None) -> list[WifiNetwork]:
        """Scan for available WiFi networks.

        Args:
            interface: Specific interface to scan (None for default)

        Returns:
            List of discovered WiFi networks

        """
        # Delegate to existing function for backward compatibility
        try:
            from atlas.network import scan_wifi_networks

            networks = await scan_wifi_networks(interface)
            if LOGURU_AVAILABLE:
                logger.debug(f"Scanned {len(networks)} WiFi networks")
            else:
                logger.debug(f"Scanned {len(networks)} WiFi networks")
            return networks
        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Error scanning WiFi networks: {e}")
            else:
                logger.error(f"Error scanning WiFi networks: {e}")
            return []

    async def get_connectivity_status(self) -> dict[str, Any]:
        """Get overall network connectivity status.

        Returns:
            Dictionary containing connectivity information

        """
        try:
            interfaces = await self.get_network_interfaces()

            # Count interface types
            up_interfaces = [iface for iface in interfaces if getattr(iface, 'is_up', False)]
            wifi_interfaces = []  # Would need to detect wireless interfaces
            ethernet_interfaces = []  # Would need to detect ethernet interfaces

            # Simple heuristic: look for common interface names
            for iface in interfaces:
                iface_name = getattr(iface, 'name', '').lower()
                if any(name in iface_name for name in ['wlan', 'wifi', 'wireless']):
                    wifi_interfaces.append(iface)
                elif any(name in iface_name for name in ['eth', 'en', 'ethernet']):
                    ethernet_interfaces.append(iface)

            # Check if any interface has IPv4 address
            has_ipv4 = any(len(getattr(iface, 'ipv4', [])) > 0 for iface in interfaces)
            has_public_ipv4 = any(
                not ip.startswith('127.') and not ip.startswith('192.168.')
                and not ip.startswith('10.') and not ip.startswith('172.16.')
                and not ip.startswith('172.17.')
                and not ip.startswith('172.18.')
                and not ip.startswith('172.19.')
                and not ip.startswith('172.20.')
                and not ip.startswith('172.21.')
                and not ip.startswith('172.22.')
                and not ip.startswith('172.23.')
                and not ip.startswith('172.24.')
                and not ip.startswith('172.25.')
                and not ip.startswith('172.26.')
                and not ip.startswith('172.27.')
                and not ip.startswith('172.28.')
                and not ip.startswith('172.29.')
                and not ip.startswith('172.30.')
                and not ip.startswith('172.31.')
                for iface in interfaces
                for ip in getattr(iface, 'ipv4', [])
            )

            status = {
                "timestamp": time.time(),
                "interfaces_total": len(interfaces),
                "interfaces_up": len(up_interfaces),
                "wifi_interfaces": len(wifi_interfaces),
                "ethernet_interfaces": len(ethernet_interfaces),
                "has_ipv4": has_ipv4,
                "has_public_ipv4": has_public_ipv4,
                "wifi_manager": {
                    "is_connected": getattr(self._wifi_manager, 'is_connected', False),
                    "connected_ssid": getattr(self._wifi_manager, 'connected_ssid', None),
                },
                "access_point": {
                    "is_active": getattr(self._ap_manager, 'is_active', False),
                    "ssid": getattr(self._ap_manager, 'ssid', ""),
                },
                "mdns_service": {
                    "is_running": getattr(self._mdns_service, 'is_running', False),
                }
            }

            if LOGURU_AVAILABLE:
                logger.debug(f"Network connectivity status: {status}")
            else:
                logger.debug(f"Network connectivity status: {status}")
            return status

        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Error getting network connectivity status: {e}")
            else:
                logger.error(f"Error getting network connectivity status: {e}")
            return {
                "timestamp": time.time(),
                "error": str(e)
            }

    async def health_check(self) -> dict[str, Any]:
        """Perform network health check.

        Returns:
            Dictionary containing health check results

        """
        try:
            status = await self.get_connectivity_status()

            # Determine overall health
            is_healthy = (
                status.get("interfaces_up", 0) > 0 and
                status.get("has_ipv4", False)
            )

            health = {
                "timestamp": status["timestamp"],
                "healthy": is_healthy,
                "status": "healthy" if is_healthy else "degraded",
                "details": status
            }

            if LOGURU_AVAILABLE:
                logger.debug(f"Network health check: {health}")
            else:
                logger.debug(f"Network health check: {health}")
            return health

        except Exception as e:
            if LOGURU_AVAILABLE:
                logger.error(f"Error performing network health check: {e}")
            else:
                logger.error(f"Error performing network health check: {e}")
            return {
                "timestamp": time.time(),
                "healthy": False,
                "status": "error",
                "error": str(e)
            }

    # Properties for accessing managers
    @property
    def wifi_manager(self) -> WiFiManager:
        """Get WiFi manager instance."""
        return self._wifi_manager

    @property
    def ap_manager(self) -> AccessPointManager:
        """Get Access Point manager instance."""
        return self._ap_manager

    @property
    def mdns_service(self) -> MDNSService:
        """Get mDNS service instance."""
        return self._mdns_service
