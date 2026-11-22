"""mDNS/DNS-SD service discovery for Atlas OS."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Optional import for zeroconf
try:
    from zeroconf import IPVersion, ServiceInfo, Zeroconf
    ZEROCONF_AVAILABLE = True
except ImportError:
    ZEROCONF_AVAILABLE = False
    logger.debug("zeroconf not available - mDNS functionality will be limited")


class MDNSService:
    """mDNS/DNS-SD service discovery and publishing."""

    def __init__(self) -> None:
        self._zeroconf: Zeroconf | None = None
        self._services: dict[str, ServiceInfo] = {}
        self._running = False

    async def start(self) -> bool:
        """Start mDNS service.

        Returns:
            True if started successfully, False otherwise

        """
        if not ZEROCONF_AVAILABLE:
            logger.warning("mDNS service not available - zeroconf not installed")
            return False

        if self._running:
            logger.warning("mDNS service already running")
            return True

        try:
            self._zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
            self._running = True
            logger.info("mDNS service started")
            return True
        except Exception as e:
            logger.error(f"Failed to start mDNS service: {e}")
            return False

    async def stop(self) -> bool:
        """Stop mDNS service.

        Returns:
            True if stopped successfully, False otherwise

        """
        if not self._running:
            logger.warning("mDNS service not running")
            return True

        if not ZEROCONF_AVAILABLE:
            logger.warning("mDNS service not available - zeroconf not installed")
            self._running = False
            return True

        try:
            if self._zeroconf:
                # Unregister all services first
                for service_info in self._services.values():
                    self._zeroconf.unregister_service(service_info)
                self._services.clear()

                # Close zeroconf instance
                self._zeroconf.close()
                self._zeroconf = None

            self._running = False
            logger.info("mDNS service stopped")
            return True
        except Exception as e:
            logger.error(f"Error stopping mDNS service: {e}")
            return False

    async def register_service(
        self,
        service_type: str,
        name: str,
        port: int,
        properties: dict[str, str] | None = None,
        host: str = "",
    ) -> bool:
        """Register a service with mDNS.

        Args:
            service_type: Service type (e.g., "_http._tcp.local.")
            name: Service instance name
            port: Port number the service is listening on
            properties: Service properties (TXT record)
            host: Hostname (if empty, uses system hostname)

        Returns:
            True if registered successfully, False otherwise

        """
        if not ZEROCONF_AVAILABLE:
            logger.warning("mDNS service not available - zeroconf not installed")
            return False

        if not self._running or not self._zeroconf:
            logger.error("mDNS service not running")
            return False

        try:
            if not host:
                import socket
                host = socket.gethostname()

            service_info = ServiceInfo(
                type_=service_type,
                name=f"{name}.{service_type}",
                addresses=[socket.inet_aton(addr) for addr in self._get_local_ips()],
                port=port,
                weight=0,
                priority=0,
                properties=properties or {},
                server=f"{host}.",
            )

            self._zeroconf.register_service(service_info)
            self._services[service_info.name] = service_info

            logger.info(f"Registered mDNS service: {name}")
            return True
        except Exception as e:
            logger.error(f"Error registering mDNS service {name}: {e}")
            return False

    async def unregister_service(self, name: str) -> bool:
        """Unregister a service from mDNS.

        Args:
            name: Service instance name to unregister

        Returns:
            True if unregistered successfully, False otherwise

        """
        if not ZEROCONF_AVAILABLE:
            logger.warning("mDNS service not available - zeroconf not installed")
            return False

        if not self._running or not self._zeroconf:
            logger.error("mDNS service not running")
            return False

        try:
            service_info = self._services.get(name)
            if service_info:
                self._zeroconf.unregister_service(service_info)
                del self._services[name]
                logger.info(f"Unregistered mDNS service: {name}")
                return True
            else:
                logger.warning(f"mDNS service not found: {name}")
                return False
        except Exception as e:
            logger.error(f"Error unregistering mDNS service {name}: {e}")
            return False

    async def browse_services(
        self,
        service_type: str,
        timeout: int = 5
    ) -> list[dict[str, Any]]:
        """Browse for services of a specific type.

        Args:
            service_type: Service type to browse for (e.g., "_http._tcp.local.")
            timeout: Browse timeout in seconds

        Returns:
            List of discovered services

        """
        if not ZEROCONF_AVAILABLE:
            logger.warning("mDNS service not available - zeroconf not installed")
            return []

        if not self._running or not self._zeroconf:
            logger.error("mDNS service not running")
            return []

        try:
            # This is a simplified implementation
            # A full implementation would use ServiceBrowser and listen for events
            logger.warning("mDNS browsing not fully implemented")
            return []
        except Exception as e:
            logger.error(f"Error browsing mDNS services: {e}")
            return []

    def _get_local_ips(self) -> list[str]:
        """Get local IP addresses.

        Returns:
            List of local IPv4 addresses

        """
        try:
            import socket

            import psutil

            ips = []
            for _interface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET:
                        ips.append(addr.address)
            return ips
        except Exception:
            # Fallback to localhost
            return ["127.0.0.1"]

    @property
    def is_running(self) -> bool:
        """Check if mDNS service is currently running."""
        return self._running
