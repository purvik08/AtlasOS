"""Network and Wi-Fi tools for Atlas OS AI."""

from __future__ import annotations

import logging
from typing import Any

from atlas.ai.tools.base import BaseTool, ToolParameter, ToolPermissionLevel, ToolResult
from atlas.network.service import NetworkService

logger = logging.getLogger(__name__)


class GetNetworkStatusTool(BaseTool):
    """Tool to check current network connectivity, active SSID, and interfaces."""

    name = "get_network_status"
    description = "Check network connectivity status, active Wi-Fi SSID, internet access, and network interfaces."
    permission_level = ToolPermissionLevel.READ_ONLY
    parameters = []

    def __init__(self, network_service: NetworkService | None = None) -> None:
        self._network_service = network_service

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            svc = self._network_service or NetworkService()
            status = await svc.connection_status()
            devices = await svc.list_devices()

            data = {
                "connected": status.connected,
                "connectivity": status.connectivity,
                "primary_device": status.primary_device,
                "primary_type": status.primary_type.value if status.primary_type else None,
                "active_ssid": status.active_ssid,
                "devices": [
                    {
                        "iface": getattr(d, "iface", getattr(d, "name", "")),
                        "type": d.device_type.value if hasattr(d.device_type, "value") else str(d.device_type),
                        "state": d.state.value if hasattr(d.state, "value") else str(d.state),
                        "ip": d.ip4_addresses[0] if getattr(d, "ip4_addresses", None) else "",
                    }
                    for d in devices
                ],
            }
            return ToolResult(success=True, data=data)
        except Exception as exc:
            return ToolResult(success=False, data=None, error=str(exc))


class ScanWifiNetworksTool(BaseTool):
    """Tool to scan nearby Wi-Fi access points."""

    name = "scan_wifi_networks"
    description = "Scan for visible Wi-Fi networks, signal strength, security type, and frequency."
    permission_level = ToolPermissionLevel.READ_ONLY
    parameters = [
        ToolParameter(
            name="interface",
            param_type="string",
            description="Optional wireless interface name (e.g. 'wlan0')",
            required=False,
            default=None,
        )
    ]

    def __init__(self, network_service: NetworkService | None = None) -> None:
        self._network_service = network_service

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            svc = self._network_service or NetworkService()
            iface = kwargs.get("interface")
            networks = await svc.scan_wifi(iface)
            data = [
                {
                    "ssid": n.ssid,
                    "signal_strength": n.signal_strength,
                    "security": n.security,
                    "in_use": n.in_use,
                }
                for n in networks
            ]
            return ToolResult(success=True, data=data)
        except Exception as exc:
            return ToolResult(success=False, data=None, error=str(exc))
