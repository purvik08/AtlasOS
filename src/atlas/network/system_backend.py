"""Cross-platform system network backend for Atlas OS.

Provides real network inspection, interface discovery, and Wi-Fi scanning
on non-Linux platforms (Windows, macOS) or Linux systems without NetworkManager DBus.
"""

from __future__ import annotations

import asyncio
import logging
import platform
import socket
from typing import Any

import psutil

from atlas.network.backend import NetworkBackend, NetworkBackendError
from atlas.network.models import (
    ConnectResult,
    ConnectResultCode,
    ConnectionStatus,
    DeviceState,
    DeviceType,
    NetworkDevice,
    WifiNetwork,
)

logger = logging.getLogger(__name__)


class SystemNetworkBackend(NetworkBackend):
    """Fallback network backend using cross-platform system primitives."""

    async def is_available(self) -> bool:
        """Always available where psutil can inspect network interfaces."""
        return True

    def _infer_device_type(self, iface_name: str) -> DeviceType:
        name = iface_name.lower()
        if any(w in name for w in ("wlan", "wifi", "wi-fi", "wireless")):
            return DeviceType.WIFI
        elif any(e in name for e in ("eth", "en", "ethernet", "lan")):
            return DeviceType.ETHERNET
        elif "lo" in name or "loopback" in name:
            return DeviceType.LOOPBACK
        return DeviceType.OTHER

    async def list_devices(self) -> list[NetworkDevice]:
        """Discover real system network devices via psutil."""
        devices: list[NetworkDevice] = []
        try:
            stats = psutil.net_if_stats()
            addrs = psutil.net_if_addrs()

            for iface, stat in stats.items():
                dev_type = self._infer_device_type(iface)
                state = DeviceState.ACTIVATED if stat.isup else DeviceState.DISCONNECTED
                mac = ""
                ip4_addrs: list[str] = []
                ip6_addrs: list[str] = []

                for addr in addrs.get(iface, []):
                    if addr.family == psutil.AF_LINK:
                        mac = addr.address or ""
                    elif addr.family == socket.AF_INET:
                        if addr.address:
                            ip4_addrs.append(addr.address)
                    elif hasattr(socket, "AF_INET6") and addr.family == socket.AF_INET6:
                        if addr.address:
                            ip6_addrs.append(addr.address)

                devices.append(
                    NetworkDevice(
                        iface=iface,
                        device_type=dev_type,
                        state=state,
                        hw_address=mac,
                        ip4_addresses=ip4_addrs,
                        ip6_addresses=ip6_addrs,
                        driver=platform.system(),
                    )
                )
        except Exception as exc:
            logger.debug("Failed to list system devices: %s", exc)
        return devices

    async def _get_active_wifi_ssid(self) -> str | None:
        """Query active Wi-Fi SSID cross-platform."""
        import subprocess

        def _query_ssid() -> str | None:
            sys_name = platform.system()
            if sys_name == "Windows":
                try:
                    res = subprocess.run(
                        ["netsh", "wlan", "show", "interfaces"],
                        capture_output=True,
                        text=True,
                        timeout=2.0,
                    )
                    if res.returncode == 0:
                        for line in res.stdout.splitlines():
                            line = line.strip()
                            if line.startswith("SSID") and ":" in line and not line.startswith("BSSID"):
                                return line.split(":", 1)[1].strip()
                except Exception:
                    pass
            elif sys_name == "Linux":
                try:
                    res = subprocess.run(
                        ["iwgetid", "-r"],
                        capture_output=True,
                        text=True,
                        timeout=2.0,
                    )
                    if res.returncode == 0 and res.stdout.strip():
                        return res.stdout.strip()
                except Exception:
                    pass
                try:
                    res = subprocess.run(
                        ["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"],
                        capture_output=True,
                        text=True,
                        timeout=2.0,
                    )
                    if res.returncode == 0:
                        for line in res.stdout.splitlines():
                            if line.startswith("yes:"):
                                return line.split(":", 1)[1].strip()
                except Exception:
                    pass
            return None

        return await asyncio.to_thread(_query_ssid)

    async def connection_status(self) -> ConnectionStatus:
        """Determine real network connectivity and active interface."""
        devices = await self.list_devices()
        active_ssid = await self._get_active_wifi_ssid()

        primary_device: str | None = None
        primary_type: DeviceType | None = None
        is_connected = False

        for dev in devices:
            if dev.device_type != DeviceType.LOOPBACK and dev.state == DeviceState.ACTIVATED:
                # If it has non-loopback IP, it's connected
                valid_ips = [ip for ip in dev.ip4_addresses if not ip.startswith("127.")]
                if valid_ips:
                    is_connected = True
                    if primary_device is None or (active_ssid and dev.device_type == DeviceType.WIFI):
                        primary_device = dev.iface
                        primary_type = dev.device_type

        return ConnectionStatus(
            connected=is_connected,
            connectivity="full" if is_connected else "none",
            primary_device=primary_device,
            primary_type=primary_type,
            active_ssid=active_ssid,
        )

    async def scan_wifi(self, iface: str | None = None) -> list[WifiNetwork]:
        """Scan Wi-Fi access points using CLI network helpers."""
        from atlas.cli.network import scan_wifi_networks
        cli_nets = await scan_wifi_networks(iface)
        results: list[WifiNetwork] = []
        active_ssid = await self._get_active_wifi_ssid()

        for n in cli_nets:
            strength = max(0, min(100, 100 + n.signal_dbm))
            results.append(
                WifiNetwork(
                    ssid=n.ssid,
                    bssid=n.bssid,
                    signal_strength=strength,
                    signal_dbm=n.signal_dbm,
                    channel=n.channel,
                    frequency_mhz=n.frequency_mhz,
                    security=n.security,
                    mode=n.mode,
                    in_use=bool(active_ssid and n.ssid == active_ssid),
                )
            )
        # Sort strongest first
        results.sort(key=lambda x: x.signal_strength, reverse=True)
        return results

    async def connect_wifi(
        self,
        ssid: str,
        password: str | None = None,
        iface: str | None = None,
    ) -> ConnectResult:
        """Connect to Wi-Fi cross-platform."""
        sys_name = platform.system()
        if sys_name == "Windows":
            import tempfile
            from xml.sax.saxutils import escape

            xml_ssid = escape(ssid)
            if password:
                xml_pass = escape(password)
                profile_xml = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{xml_ssid}</name>
    <SSIDConfig>
        <SSID>
            <name>{xml_ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{xml_pass}</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>"""
            else:
                profile_xml = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{xml_ssid}</name>
    <SSIDConfig>
        <SSID>
            <name>{xml_ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>open</authentication>
                <encryption>none</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
        </security>
    </MSM>
</WLANProfile>"""

            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False, encoding="utf-8") as f:
                    f.write(profile_xml)
                    tmp_path = f.name

                add_proc = await asyncio.create_subprocess_exec(
                    "netsh", "wlan", "add", "profile", f"filename={tmp_path}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await add_proc.communicate()

                connect_args = ["netsh", "wlan", "connect", f"name={ssid}"]
                if iface:
                    connect_args.append(f"interface={iface}")

                proc = await asyncio.create_subprocess_exec(
                    *connect_args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                out_msg = (stdout.decode(errors="replace") + stderr.decode(errors="replace")).strip()
                if proc.returncode == 0:
                    return ConnectResult(code=ConnectResultCode.SUCCESS, message=f"Connected to {ssid}", device=iface)
                return ConnectResult(
                    code=ConnectResultCode.ERROR,
                    message=out_msg or "Connection failed",
                    device=iface,
                )
            except Exception as exc:
                return ConnectResult(code=ConnectResultCode.ERROR, message=str(exc), device=iface)
            finally:
                if tmp_path:
                    import os
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass

        elif sys_name == "Linux":
            # Try nmcli CLI fallback if NetworkManager DBus was unavailable
            try:
                cmd = ["nmcli", "dev", "wifi", "connect", ssid]
                if password:
                    cmd.extend(["password", password])
                if iface:
                    cmd.extend(["ifname", iface])

                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                out_text = (stdout.decode(errors="replace") + stderr.decode(errors="replace")).strip()
                if proc.returncode == 0:
                    return ConnectResult(code=ConnectResultCode.SUCCESS, message=f"Connected to {ssid}", device=iface)
                return ConnectResult(
                    code=ConnectResultCode.ERROR,
                    message=out_text or "nmcli connect failed",
                    device=iface,
                )
            except Exception as exc:
                return ConnectResult(code=ConnectResultCode.ERROR, message=str(exc), device=iface)

        return ConnectResult(
            code=ConnectResultCode.BACKEND_UNAVAILABLE,
            message=f"Wi-Fi connection not supported on {sys_name} without NetworkManager.",
            device=iface,
        )

    async def disconnect(self, iface: str | None = None) -> bool:
        """Disconnect Wi-Fi."""
        sys_name = platform.system()
        if sys_name == "Windows":
            try:
                cmd = ["netsh", "wlan", "disconnect"]
                if iface:
                    cmd.append(f"interface={iface}")
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
                return proc.returncode == 0
            except Exception:
                return False
        elif sys_name == "Linux":
            try:
                cmd = ["nmcli", "dev", "disconnect", iface or "wlan0"]
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
                return proc.returncode == 0
            except Exception:
                return False
        return False
