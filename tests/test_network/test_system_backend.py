"""Unit tests for SystemNetworkBackend (cross-platform fallback)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from atlas.network.models import ConnectResultCode, DeviceType
from atlas.network.system_backend import SystemNetworkBackend


@pytest.fixture
def backend():
    return SystemNetworkBackend()


@pytest.mark.asyncio
async def test_system_backend_is_available(backend):
    assert await backend.is_available() is True


@pytest.mark.asyncio
async def test_system_backend_list_devices(backend):
    devices = await backend.list_devices()
    assert isinstance(devices, list)
    for dev in devices:
        assert dev.iface != ""
        assert isinstance(dev.device_type, DeviceType)


def test_infer_device_type(backend):
    assert backend._infer_device_type("Wi-Fi") == DeviceType.WIFI
    assert backend._infer_device_type("wlan0") == DeviceType.WIFI
    assert backend._infer_device_type("Ethernet") == DeviceType.ETHERNET
    assert backend._infer_device_type("eth0") == DeviceType.ETHERNET
    assert backend._infer_device_type("lo") == DeviceType.LOOPBACK
    assert backend._infer_device_type("tun0") == DeviceType.OTHER


def test_parse_netsh_scan():
    from atlas.cli.network import _parse_netsh_scan

    netsh_output = """
Interface name : Wi-Fi
There are 2 networks currently visible.

SSID 1 : HomeNetwork
    Network type            : Infrastructure
    Authentication          : WPA2-Personal
    Encryption              : CCMP
    BSSID 1                 : 00:11:22:33:44:55
         Signal             : 85%
         Radio type         : 802.11ax
         Channel            : 6
         Basic rates (Mbps) : 1 2 5.5 11
         Other rates (Mbps) : 6 9 12 18 24 36 48 54

SSID 2 : CoffeeShop_Free
    Network type            : Infrastructure
    Authentication          : Open
    Encryption              : None
    BSSID 1                 : aa:bb:cc:dd:ee:ff
         Signal             : 60%
         Radio type         : 802.11ac
         Channel            : 36
    BSSID 2                 : aa:bb:cc:dd:ee:fe
         Signal             : 45%
         Radio type         : 802.11ac
         Channel            : 40
"""
    networks = _parse_netsh_scan(netsh_output)
    assert len(networks) >= 2

    home = next(n for n in networks if n.ssid == "HomeNetwork")
    assert home.bssid == "00:11:22:33:44:55"
    assert home.signal_dbm == -15  # -100 + 85%
    assert home.channel == 6
    assert home.security == "WPA2-Personal"

    coffee = next(n for n in networks if n.ssid == "CoffeeShop_Free")
    assert coffee.security == "Open"



@pytest.mark.asyncio
async def test_connect_wifi_windows_wpa2(backend):
    with patch("platform.system", return_value="Windows"):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"Connection request completed successfully.\r\n", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            res = await backend.connect_wifi("TestWiFi", password="supersecretpassword")
            assert res.code == ConnectResultCode.SUCCESS
            assert "Connected to TestWiFi" in res.message
            assert mock_exec.call_count == 2


@pytest.mark.asyncio
async def test_connect_wifi_windows_open(backend):
    with patch("platform.system", return_value="Windows"):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"Connection request completed successfully.\r\n", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            res = await backend.connect_wifi("OpenWiFi", password=None)
            assert res.code == ConnectResultCode.SUCCESS
            assert mock_exec.call_count == 2


@pytest.mark.asyncio
async def test_disconnect_windows(backend):
    with patch("platform.system", return_value="Windows"):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            ok = await backend.disconnect()
            assert ok is True
            mock_exec.assert_called_once_with(
                "netsh", "wlan", "disconnect",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
