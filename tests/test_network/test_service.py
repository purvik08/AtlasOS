"""Unit tests for NetworkService.

Verifies NetworkService delegation to NetworkBackend, graceful fallback,
and convenience methods. Uses mock backends — no real hardware required.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from atlas.network.backend import NetworkBackend, NetworkBackendError
from atlas.network.models import (
    ConnectResult,
    ConnectResultCode,
    ConnectionStatus,
    DeviceType,
    NetworkDevice,
    DeviceState,
    WifiNetwork,
)
from atlas.network.service import NetworkService


class MockNetworkBackend(NetworkBackend):
    """Test double for NetworkBackend."""

    def __init__(self, available: bool = True) -> None:
        self._available = available
        self.scan_result: list[WifiNetwork] = []
        self.connect_result: ConnectResult = ConnectResult(
            code=ConnectResultCode.SUCCESS, message="OK"
        )
        self.disconnect_result: bool = True
        self.status_result: ConnectionStatus = ConnectionStatus(
            connected=True,
            connectivity="full",
            primary_device="wlan0",
            primary_type=DeviceType.WIFI,
            active_ssid="TestNet",
        )

    async def is_available(self) -> bool:
        return self._available

    async def scan_wifi(self, iface=None) -> list[WifiNetwork]:
        return self.scan_result

    async def list_devices(self) -> list[NetworkDevice]:
        return []

    async def connect_wifi(self, ssid, password=None, iface=None) -> ConnectResult:
        return self.connect_result

    async def disconnect(self, iface=None) -> bool:
        return self.disconnect_result

    async def connection_status(self) -> ConnectionStatus:
        return self.status_result


class TestNetworkService:
    @pytest.mark.asyncio
    async def test_is_available_delegates_to_backend(self):
        backend = MockNetworkBackend(available=True)
        svc = NetworkService(backend=backend)
        assert await svc.is_available() is True

    @pytest.mark.asyncio
    async def test_is_available_caches_result(self):
        backend = MockNetworkBackend(available=True)
        svc = NetworkService(backend=backend)
        await svc.is_available()
        # Second call should use cached result
        await svc.is_available()
        assert svc._available is True

    @pytest.mark.asyncio
    async def test_scan_wifi_returns_backend_results(self):
        backend = MockNetworkBackend()
        backend.scan_result = [
            WifiNetwork("Net1", "AA:BB:CC:DD:EE:01", 90, -50, 6, 2437, "WPA2", "Infrastructure"),
            WifiNetwork("Net2", "AA:BB:CC:DD:EE:02", 60, -70, 1, 2412, "Open", "Infrastructure"),
        ]
        svc = NetworkService(backend=backend)
        result = await svc.scan_wifi()
        assert len(result) == 2
        assert result[0].ssid == "Net1"

    @pytest.mark.asyncio
    async def test_scan_wifi_raises_when_unavailable(self):
        backend = MockNetworkBackend(available=False)
        svc = NetworkService(backend=backend)
        with pytest.raises(NetworkBackendError):
            await svc.scan_wifi()

    @pytest.mark.asyncio
    async def test_connect_wifi_success(self):
        backend = MockNetworkBackend()
        backend.connect_result = ConnectResult(
            code=ConnectResultCode.SUCCESS, message="Connected", device="wlan0"
        )
        svc = NetworkService(backend=backend)
        result = await svc.connect_wifi("TestNet", "password123")
        assert result.success is True
        assert result.device == "wlan0"

    @pytest.mark.asyncio
    async def test_connect_wifi_auth_failed(self):
        backend = MockNetworkBackend()
        backend.connect_result = ConnectResult(
            code=ConnectResultCode.AUTH_FAILED, message="Bad password"
        )
        svc = NetworkService(backend=backend)
        result = await svc.connect_wifi("TestNet", "wrong")
        assert result.success is False
        assert result.code == ConnectResultCode.AUTH_FAILED

    @pytest.mark.asyncio
    async def test_disconnect_delegates(self):
        backend = MockNetworkBackend()
        svc = NetworkService(backend=backend)
        result = await svc.disconnect()
        assert result is True

    @pytest.mark.asyncio
    async def test_connection_status_returns_connected(self):
        backend = MockNetworkBackend()
        svc = NetworkService(backend=backend)
        status = await svc.connection_status()
        assert status.connected is True
        assert status.active_ssid == "TestNet"

    @pytest.mark.asyncio
    async def test_connection_status_returns_safe_defaults_when_unavailable(self):
        backend = MockNetworkBackend(available=False)
        svc = NetworkService(backend=backend)
        # Should NOT raise; returns safe defaults
        status = await svc.connection_status()
        assert status.connected is False
        assert status.connectivity == "unknown"

    @pytest.mark.asyncio
    async def test_is_connected_convenience(self):
        backend = MockNetworkBackend()
        svc = NetworkService(backend=backend)
        assert await svc.is_connected() is True

    @pytest.mark.asyncio
    async def test_active_wifi_ssid(self):
        backend = MockNetworkBackend()
        svc = NetworkService(backend=backend)
        assert await svc.active_wifi_ssid() == "TestNet"

    @pytest.mark.asyncio
    async def test_list_devices_returns_empty_when_unavailable(self):
        backend = MockNetworkBackend(available=False)
        svc = NetworkService(backend=backend)
        result = await svc.list_devices()
        assert result == []

    def test_to_dict_contains_backend_name(self):
        backend = MockNetworkBackend()
        svc = NetworkService(backend=backend)
        d = svc.to_dict()
        assert "MockNetworkBackend" in d["backend"]
