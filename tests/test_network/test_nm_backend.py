"""Unit tests for NetworkManagerBackend.

All DBus calls are mocked — no real NetworkManager or dbus-next required.
These tests run in CI on any platform.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from atlas.network.models import (
    ConnectResultCode,
    ConnectionStatus,
    DeviceState,
    DeviceType,
    WifiNetwork,
)


class TestWifiNetworkModel:
    """Tests for the WifiNetwork dataclass."""

    def test_to_dict_has_all_fields(self):
        net = WifiNetwork(
            ssid="TestNet",
            bssid="AA:BB:CC:DD:EE:FF",
            signal_strength=75,
            signal_dbm=-60,
            channel=6,
            frequency_mhz=2437,
            security="WPA2",
            mode="Infrastructure",
            in_use=True,
        )
        d = net.to_dict()
        assert d["ssid"] == "TestNet"
        assert d["bssid"] == "AA:BB:CC:DD:EE:FF"
        assert d["signal_strength"] == 75
        assert d["security"] == "WPA2"
        assert d["in_use"] is True

    def test_to_dict_defaults(self):
        net = WifiNetwork(
            ssid="Open",
            bssid="00:00:00:00:00:00",
            signal_strength=50,
            signal_dbm=-60,
            channel=1,
            frequency_mhz=2412,
            security="Open",
            mode="Infrastructure",
        )
        assert net.in_use is False


class TestConnectionStatus:
    def test_to_dict_connected(self):
        status = ConnectionStatus(
            connected=True,
            connectivity="full",
            primary_device="wlan0",
            primary_type=DeviceType.WIFI,
            active_ssid="HomeNetwork",
        )
        d = status.to_dict()
        assert d["connected"] is True
        assert d["connectivity"] == "full"
        assert d["primary_type"] == "wifi"
        assert d["active_ssid"] == "HomeNetwork"

    def test_to_dict_disconnected(self):
        status = ConnectionStatus(
            connected=False,
            connectivity="none",
            primary_device=None,
            primary_type=None,
            active_ssid=None,
        )
        d = status.to_dict()
        assert d["connected"] is False
        assert d["primary_type"] is None


class TestNMBackendUnavailable:
    """Tests for NM backend when dbus-next is not installed."""

    def test_is_available_false_without_dbus(self):
        """Backend should not be available when dbus-next is missing."""
        with patch("atlas.network.nm_backend._DBUS_AVAILABLE", False):
            from atlas.network.nm_backend import NetworkManagerBackend
            backend = NetworkManagerBackend()

            import asyncio
            result = asyncio.run(backend.is_available())
            assert result is False

    def test_is_available_false_on_non_linux(self):
        """Backend should not be available on non-Linux platforms."""
        with patch("atlas.network.nm_backend._DBUS_AVAILABLE", True), \
             patch("atlas.network.nm_backend.platform.system", return_value="Darwin"):
            from atlas.network.nm_backend import NetworkManagerBackend
            backend = NetworkManagerBackend()
            import asyncio
            result = asyncio.run(backend.is_available())
            assert result is False


class TestNMBackendMocked:
    """Tests for NM backend with mocked MessageBus."""

    @pytest.fixture
    def mock_bus(self):
        """Provide a mock dbus MessageBus."""
        bus = AsyncMock()
        return bus

    @pytest.mark.asyncio
    async def test_scan_returns_empty_on_no_wifi_devices(self):
        """Scan should return empty list when no Wi-Fi devices found."""
        with patch("atlas.network.nm_backend._DBUS_AVAILABLE", True), \
             patch("atlas.network.nm_backend.platform.system", return_value="Linux"):
            from atlas.network.nm_backend import NetworkManagerBackend
            backend = NetworkManagerBackend()

            # Mock _get_wifi_devices to return empty
            backend._get_wifi_devices = AsyncMock(return_value=[])
            result = await backend.scan_wifi()
            assert result == []

    @pytest.mark.asyncio
    async def test_connect_returns_device_not_found_with_no_wifi(self):
        """Connect should return DEVICE_NOT_FOUND when no Wi-Fi device exists."""
        with patch("atlas.network.nm_backend._DBUS_AVAILABLE", True), \
             patch("atlas.network.nm_backend.platform.system", return_value="Linux"):
            from atlas.network.nm_backend import NetworkManagerBackend
            backend = NetworkManagerBackend()
            backend._get_wifi_devices = AsyncMock(return_value=[])

            result = await backend.connect_wifi("MySSID", "password")
            assert result.code == ConnectResultCode.DEVICE_NOT_FOUND
            assert not result.success

    @pytest.mark.asyncio
    async def test_disconnect_returns_false_with_no_wifi(self):
        """Disconnect should return False when no Wi-Fi device exists."""
        with patch("atlas.network.nm_backend._DBUS_AVAILABLE", True), \
             patch("atlas.network.nm_backend.platform.system", return_value="Linux"):
            from atlas.network.nm_backend import NetworkManagerBackend
            backend = NetworkManagerBackend()
            backend._get_wifi_devices = AsyncMock(return_value=[])

            result = await backend.disconnect()
            assert result is False

    @pytest.mark.asyncio
    async def test_connection_status_returns_disconnected_on_error(self):
        """connection_status should return safe defaults on backend error."""
        with patch("atlas.network.nm_backend._DBUS_AVAILABLE", True), \
             patch("atlas.network.nm_backend.platform.system", return_value="Linux"):
            from atlas.network.nm_backend import NetworkManagerBackend
            backend = NetworkManagerBackend()
            # Force an error in the internal method
            backend._get_nm_proxy = AsyncMock(side_effect=Exception("DBus error"))

            result = await backend.connection_status()
            assert result.connected is False
            assert result.connectivity == "unknown"


class TestNMUtilFunctions:
    """Tests for pure utility functions in nm_backend."""

    def test_freq_to_channel_24ghz(self):
        from atlas.network.nm_backend import _freq_to_channel
        assert _freq_to_channel(2412) == 1
        assert _freq_to_channel(2437) == 6
        assert _freq_to_channel(2462) == 11

    def test_freq_to_channel_5ghz(self):
        from atlas.network.nm_backend import _freq_to_channel
        assert _freq_to_channel(5180) == 36
        assert _freq_to_channel(5805) == 161

    def test_freq_to_channel_unknown(self):
        from atlas.network.nm_backend import _freq_to_channel
        assert _freq_to_channel(0) == 0

    def test_determine_security_wpa2(self):
        from atlas.network.nm_backend import _determine_security
        # RSN flags set = WPA2
        assert _determine_security(1, 0, 324) == "WPA2"

    def test_determine_security_wpa(self):
        from atlas.network.nm_backend import _determine_security
        assert _determine_security(1, 260, 0) == "WPA"

    def test_determine_security_open(self):
        from atlas.network.nm_backend import _determine_security
        assert _determine_security(0, 0, 0) == "Open"

    def test_determine_security_wep(self):
        from atlas.network.nm_backend import _determine_security
        # flags & 0x1 = privacy bit = WEP
        assert _determine_security(1, 0, 0) == "WEP"

    def test_strength_to_dbm(self):
        from atlas.network.nm_backend import _strength_to_dbm
        assert _strength_to_dbm(0) == -100
        assert _strength_to_dbm(100) == 0
        assert _strength_to_dbm(50) == -50
