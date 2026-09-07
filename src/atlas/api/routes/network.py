"""Network management routes for Atlas OS API."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from atlas.api.auth import require_auth
from atlas.network import NetworkService
from atlas.runtime.application import AtlasApplication

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/network", tags=["network"])


class WifiConnectRequest(BaseModel):
    """Request to connect to a Wi-Fi network."""
    ssid: str
    password: str | None = None
    iface: str | None = None


def get_app(request: Request) -> AtlasApplication:
    return request.app.state.atlas_app


@router.get("/status")
async def network_status(
    app: AtlasApplication = Depends(get_app),
    api_key: Any = Depends(require_auth),
) -> dict[str, Any]:
    """Get network connectivity status and active interfaces."""
    svc = NetworkService()
    status = await svc.connection_status()
    devices = await svc.list_devices()

    # Also query system interfaces via psutil
    from atlas.cli.network import get_network_interfaces
    ifaces = get_network_interfaces()

    return {
        "connected": status.connected,
        "connectivity": status.connectivity,
        "primary_device": status.primary_device,
        "primary_type": status.primary_type.value if status.primary_type else None,
        "active_ssid": status.active_ssid,
        "devices": [
            {
                "name": getattr(d, "iface", getattr(d, "name", "")),
                "iface": getattr(d, "iface", getattr(d, "name", "")),
                "type": d.device_type.value if hasattr(d.device_type, "value") else str(d.device_type),
                "state": d.state.value if hasattr(d.state, "value") else str(d.state),
                "mac": getattr(d, "hw_address", getattr(d, "mac", "")),
                "ip": d.ip4_addresses[0] if getattr(d, "ip4_addresses", None) else getattr(d, "ip", ""),
                "ip4_addresses": getattr(d, "ip4_addresses", []),
                "ip6_addresses": getattr(d, "ip6_addresses", []),
            }
            for d in devices
        ],
        "interfaces": [
            {
                "name": i.name,
                "up": i.is_up,
                "ipv4": i.ipv4,
                "ipv6": i.ipv6,
                "mac": i.mac,
                "speed_mbps": i.speed,
            }
            for i in ifaces
        ],
    }


@router.get("/wifi/scan")
async def scan_wifi(
    iface: str | None = Query(None, description="Wireless interface name"),
    app: AtlasApplication = Depends(get_app),
    api_key: Any = Depends(require_auth),
) -> list[dict[str, Any]]:
    """Scan for available Wi-Fi networks."""
    svc = NetworkService()
    try:
        networks = await svc.scan_wifi(iface)
        return [
            {
                "ssid": n.ssid,
                "bssid": n.bssid,
                "signal_strength": n.signal_strength,
                "security": n.security,
                "frequency_mhz": n.frequency_mhz,
                "in_use": n.in_use,
            }
            for n in networks
        ]
    except Exception as exc:
        # Fallback to platform-specific CLI scan tool
        from atlas.cli.network import scan_wifi_networks
        cli_nets = await scan_wifi_networks(iface)
        return [
            {
                "ssid": n.ssid,
                "bssid": n.bssid,
                "signal_strength": max(0, min(100, 100 + n.signal_dbm)),
                "security": n.security,
                "frequency_mhz": n.frequency_mhz,
                "in_use": False,
            }
            for n in cli_nets
        ]


@router.post("/wifi/connect")
async def connect_wifi(
    request: WifiConnectRequest,
    app: AtlasApplication = Depends(get_app),
    api_key: Any = Depends(require_auth),
) -> dict[str, Any]:
    """Connect to a Wi-Fi network."""
    svc = NetworkService()
    try:
        res = await svc.connect_wifi(request.ssid, request.password, request.iface)
        return {
            "success": res.success,
            "code": res.code.value,
            "message": res.message,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/wifi/disconnect")
async def disconnect_wifi(
    iface: str | None = Query(None),
    app: AtlasApplication = Depends(get_app),
    api_key: Any = Depends(require_auth),
) -> dict[str, Any]:
    """Disconnect active Wi-Fi connection."""
    svc = NetworkService()
    try:
        ok = await svc.disconnect(iface)
        return {"success": ok, "message": "Disconnected" if ok else "Failed"}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
