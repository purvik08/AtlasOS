"""Network management commands for Atlas OS.

Provides cross-platform network interface management, Wi-Fi scanning,
Access Point control, and mDNS service discovery.
"""

from __future__ import annotations

import asyncio
import json
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import anyio
import click
import socket
import psutil
from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class NetworkInterface:
    """Network interface information."""
    name: str
    is_up: bool
    ipv4: list[str]
    ipv6: list[str]
    mac: str | None
    mtu: int
    speed: int | None
    flags: list[str]


@dataclass
class WifiNetwork:
    """Wi-Fi network scan result."""
    ssid: str
    bssid: str
    signal_dbm: int
    channel: int
    frequency_mhz: int
    security: str
    mode: str


def get_network_interfaces() -> list[NetworkInterface]:
    """Get all network interfaces with their details."""
    interfaces: list[NetworkInterface] = []
    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()

    for name, stat in stats.items():
        ipv4_list: list[str] = []
        ipv6_list: list[str] = []
        mac: str | None = None

        for addr in addrs.get(name, []):
            if addr.family == psutil.AF_LINK:
                mac = addr.address
            elif addr.family == socket.AF_INET:
                ipv4_list.append(addr.address)
            elif addr.family == socket.AF_INET6:
                ipv6_list.append(addr.address)

        flags: list[str] = []
        if stat.isup:
            flags.append("UP")
        try:
            flag_val = int(stat.flags)
        except (ValueError, TypeError):
            flag_val = 0
        if flag_val & 0x1:  # BROADCAST
            flags.append("BROADCAST")
        if flag_val & 0x2:  # DEBUG
            flags.append("DEBUG")
        if flag_val & 0x4:  # LOOPBACK
            flags.append("LOOPBACK")
        if flag_val & 0x8:  # POINTOPOINT
            flags.append("POINTOPOINT")
        if flag_val & 0x10:  # NOTRAILERS
            flags.append("NOTRAILERS")
        if flag_val & 0x20:  # RUNNING
            flags.append("RUNNING")
        if flag_val & 0x40:  # NOARP
            flags.append("NOARP")
        if flag_val & 0x80:  # PROMISC
            flags.append("PROMISC")
        if flag_val & 0x100:  # ALLMULTI
            flags.append("ALLMULTI")
        if flag_val & 0x200:  # MASTER
            flags.append("MASTER")
        if flag_val & 0x400:  # SLAVE
            flags.append("SLAVE")
        if flag_val & 0x800:  # MULTICAST
            flags.append("MULTICAST")

        interfaces.append(NetworkInterface(
            name=name,
            is_up=stat.isup,
            ipv4=ipv4_list,
            ipv6=ipv6_list,
            mac=mac,
            mtu=stat.mtu,
            speed=stat.speed if stat.speed > 0 else None,
            flags=flags,
        ))

    return interfaces


def _decode_bytes(data: bytes) -> str:
    """Decode subprocess output using encodings common on Windows netsh."""
    if not data:
        return ""
    for encoding in ("utf-8", "oem", "cp437", "cp1252"):
        try:
            return data.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return data.decode("utf-8", errors="replace")


async def scan_wifi_networks(interface: str | None = None) -> list[WifiNetwork]:
    """Scan for Wi-Fi networks using platform-specific tools."""
    system = platform.system().lower()
    networks: list[WifiNetwork] = []

    try:
        if system == "linux":
            networks = await _scan_wifi_linux(interface)
        elif system == "windows":
            networks = await _scan_wifi_windows()
        elif system == "darwin":
            networks = await _scan_wifi_macos()
        else:
            console.print(f"[yellow]WiFi scanning not supported on {system}[/]")
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]WiFi scan failed: {exc}[/]")

    return networks


async def _scan_wifi_linux(interface: str | None) -> list[WifiNetwork]:
    """Scan Wi-Fi on Linux using iw/iwlist/nmcli."""
    networks: list[WifiNetwork] = []

    # Try nmcli first (NetworkManager)
    try:
        fields = "SSID,BSSID,SIGNAL,CHAN,FREQ,SECURITY,MODE"
        cmd = ["nmcli", "-t", "-f", fields, "dev", "wifi", "list"]
        if interface:
            cmd.extend(["ifname", interface])
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            for line in stdout.decode().strip().split("\n"):
                if not line:
                    continue
                parts = line.split(":")
                if len(parts) >= 7:
                    networks.append(WifiNetwork(
                        ssid=parts[0] or "(hidden)",
                        bssid=parts[1],
                        signal_dbm=int(parts[2]) - 100 if parts[2].isdigit() else -100,
                        channel=int(parts[3]) if parts[3].isdigit() else 0,
                        frequency_mhz=int(parts[4]) if parts[4].isdigit() else 0,
                        security=parts[5],
                        mode=parts[6],
                    ))
            return networks
    except Exception:  # noqa: BLE001
        pass

    # Fallback to iw
    try:
        iface = interface or "wlan0"
        proc = await asyncio.create_subprocess_exec(
            "iw", "dev", iface, "scan",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            networks = _parse_iw_scan(stdout.decode())
    except Exception:  # noqa: BLE001
        pass

    return networks


def _parse_iw_scan(output: str) -> list[WifiNetwork]:
    """Parse iw scan output."""
    networks: list[WifiNetwork] = []
    current: dict[str, Any] = {}

    for line in output.split("\n"):
        line = line.strip()
        if line.startswith("BSS "):
            if current:
                networks.append(_build_network(current))
            current = {"bssid": line.split(" ")[1].split("(")[0]}
        elif "SSID:" in line:
            current["ssid"] = line.split("SSID: ")[1]
        elif "signal:" in line:
            current["signal"] = line.split("signal: ")[1].split(" ")[0]
        elif "freq:" in line:
            current["freq"] = line.split("freq: ")[1].split(" ")[0]
        elif "channel" in line.lower():
            current["channel"] = line.split()[-1]
        elif "capability:" in line:
            current["security"] = line.split("capability: ")[1]

    if current:
        networks.append(_build_network(current))

    return networks


def _build_network(data: dict[str, Any]) -> WifiNetwork:
    """Build WifiNetwork from parsed data."""
    signal = data.get("signal", "-100")
    try:
        signal_dbm = int(signal)
    except ValueError:
        signal_dbm = -100

    freq = data.get("freq", "0")
    try:
        freq_mhz = int(freq)
    except ValueError:
        freq_mhz = 0

    channel = data.get("channel", "0")
    try:
        ch = int(channel)
    except ValueError:
        ch = 0

    return WifiNetwork(
        ssid=data.get("ssid", "(hidden)"),
        bssid=data.get("bssid", "00:00:00:00:00:00"),
        signal_dbm=signal_dbm,
        channel=ch,
        frequency_mhz=freq_mhz,
        security=data.get("security", "Unknown"),
        mode="Infrastructure",
    )


async def _scan_wifi_windows() -> list[WifiNetwork]:
    """Scan Wi-Fi on Windows using netsh."""
    networks: list[WifiNetwork] = []
    try:
        proc = await asyncio.create_subprocess_exec(
            "netsh", "wlan", "show", "networks", "mode=bssid",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            networks = _parse_netsh_scan(_decode_bytes(stdout))
    except Exception:  # noqa: BLE001
        pass
    return networks


def _parse_netsh_scan(output: str) -> list[WifiNetwork]:
    """Parse netsh wlan show networks output."""
    networks: list[WifiNetwork] = []
    current_ssid = ""
    current_sec = "Unknown"
    current_bss: dict[str, Any] | None = None

    for line in output.splitlines():
        line = line.strip()
        if line.startswith("SSID ") and ":" in line:
            if current_bss is not None:
                networks.append(_build_netsh_network(current_bss))
                current_bss = None
            current_ssid = line.split(":", 1)[1].strip() or "(hidden)"
            current_sec = "Unknown"
        elif "Authentication" in line and ":" in line:
            current_sec = line.split(":", 1)[1].strip()
            if current_bss is not None:
                current_bss["security"] = current_sec
        elif "BSSID" in line and ":" in line:
            if current_bss is not None:
                networks.append(_build_netsh_network(current_bss))
            bssid_val = line.split(":", 1)[1].strip()
            current_bss = {
                "ssid": current_ssid,
                "bssid": bssid_val,
                "security": current_sec,
            }
        elif "Signal" in line and ":" in line and current_bss is not None:
            sig = line.split(":", 1)[1].strip().replace("%", "")
            try:
                pct = int(sig)
                current_bss["signal"] = str(-100 + pct)
            except ValueError:
                current_bss["signal"] = "-100"
        elif "Channel" in line and ":" in line and current_bss is not None:
            current_bss["channel"] = line.split(":", 1)[1].strip()

    if current_bss is not None:
        networks.append(_build_netsh_network(current_bss))
    elif current_ssid:
        networks.append(_build_netsh_network({"ssid": current_ssid, "security": current_sec}))

    return networks


def _build_netsh_network(data: dict[str, Any]) -> WifiNetwork:
    signal_str = data.get("signal", "-100")
    try:
        signal_dbm = int(signal_str)
    except ValueError:
        signal_dbm = -100

    channel_str = data.get("channel", "0")
    try:
        channel = int(channel_str)
    except ValueError:
        channel = 0

    return WifiNetwork(
        ssid=data.get("ssid", "(hidden)"),
        bssid=data.get("bssid", "00:00:00:00:00:00"),
        signal_dbm=signal_dbm,
        channel=channel,
        frequency_mhz=0,
        security=data.get("security", "Unknown"),
        mode="Infrastructure",
    )


async def _scan_wifi_macos() -> list[WifiNetwork]:
    """Scan Wi-Fi on macOS using airport utility."""
    networks: list[WifiNetwork] = []
    try:
        airport = (
            "/System/Library/PrivateFrameworks/Apple80211.framework/"
            "Versions/Current/Resources/airport"
        )
        if not await anyio.Path(airport).exists():
            return networks
        proc = await asyncio.create_subprocess_exec(
            airport, "-s",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            networks = _parse_airport_scan(stdout.decode())
    except Exception:  # noqa: BLE001
        pass
    return networks


def _parse_airport_scan(output: str) -> list[WifiNetwork]:
    """Parse airport -s output."""
    networks: list[WifiNetwork] = []
    lines = output.strip().split("\n")
    if len(lines) < 2:
        return networks

    for line in lines[1:]:  # Skip header
        parts = line.split()
        if len(parts) >= 6:
            ssid = " ".join(parts[:-5])
            networks.append(WifiNetwork(
                ssid=ssid,
                bssid=parts[-5],
                signal_dbm=int(parts[-4]),
                channel=int(parts[-3]),
                frequency_mhz=int(parts[-2]),
                security=parts[-1],
                mode="Infrastructure",
            ))
    return networks


def _signal_bar(dbm: int) -> str:
    """Convert dBm to visual signal bar."""
    if dbm >= -50:
        return "█████"
    elif dbm >= -60:
        return "████░"
    elif dbm >= -70:
        return "███░░"
    elif dbm >= -80:
        return "██░░░"
    elif dbm >= -90:
        return "█░░░░"
    return "░░░░░"


@click.group(name="network")
def network_group() -> None:
    """Manage network configuration."""
    pass


@network_group.command(name="status")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def network_status(ctx: click.Context, output_json: bool) -> None:
    """Show network interface status."""
    interfaces = get_network_interfaces()

    if output_json:
        data = [
            {
                "name": iface.name,
                "up": iface.is_up,
                "ipv4": iface.ipv4,
                "ipv6": iface.ipv6,
                "mac": iface.mac,
                "mtu": iface.mtu,
                "speed_mbps": iface.speed,
                "flags": iface.flags,
            }
            for iface in interfaces
        ]
        console.print(json.dumps(data, indent=2))
        return

    table = Table(title="Network Interfaces", box=None)
    table.add_column("Interface", style="cyan", no_wrap=True)
    table.add_column("Status", style="green")
    table.add_column("MAC", style="dim")
    table.add_column("IPv4", style="white")
    table.add_column("IPv6", style="dim")
    table.add_column("MTU", style="yellow", justify="right")
    table.add_column("Speed", style="yellow", justify="right")
    table.add_column("Flags", style="dim")

    for iface in interfaces:
        status = "[green]UP[/]" if iface.is_up else "[red]DOWN[/]"
        ipv4 = ", ".join(iface.ipv4) if iface.ipv4 else "—"
        ipv6 = ", ".join(iface.ipv6) if iface.ipv6 else "—"
        mac = iface.mac or "—"
        speed = f"{iface.speed} Mbps" if iface.speed else "—"
        flags = ", ".join(iface.flags) if iface.flags else "—"

        table.add_row(iface.name, status, mac, ipv4, ipv6, str(iface.mtu), speed, flags)

    console.print(table)


@network_group.command(name="scan")
@click.option("--interface", "-i", default=None, help="Wireless interface to scan (e.g., wlan0)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option(
    "--sort",
    type=click.Choice(["signal", "ssid", "channel"]),
    default="signal",
    help="Sort results",
)
@click.pass_context
def network_scan(ctx: click.Context, interface: str | None, output_json: bool, sort: str) -> None:
    """Scan for available Wi-Fi networks."""

    async def _scan() -> None:
        console.print("[cyan]Scanning Wi-Fi networks...[/]")
        networks = await scan_wifi_networks(interface)

        if not networks:
            msg = "No networks found or scanning not supported on this platform."
            console.print(f"[yellow]{msg}[/]")
            return

        if sort == "signal":
            networks.sort(key=lambda n: n.signal_dbm, reverse=True)
        elif sort == "ssid":
            networks.sort(key=lambda n: n.ssid.lower())
        elif sort == "channel":
            networks.sort(key=lambda n: n.channel)

        if output_json:
            data = [
                {
                    "ssid": n.ssid,
                    "bssid": n.bssid,
                    "signal_dbm": n.signal_dbm,
                    "channel": n.channel,
                    "frequency_mhz": n.frequency_mhz,
                    "security": n.security,
                    "mode": n.mode,
                }
                for n in networks
            ]
            console.print(json.dumps(data, indent=2))
            return

        table = Table(title="Wi-Fi Networks", box=None)
        table.add_column("SSID", style="cyan", no_wrap=True)
        table.add_column("BSSID", style="dim")
        table.add_column("Signal", style="green")
        table.add_column("Ch", style="yellow", justify="right")
        table.add_column("Freq (MHz)", style="dim", justify="right")
        table.add_column("Security", style="white")
        table.add_column("Mode", style="dim")

        for n in networks:
            table.add_row(
                n.ssid,
                n.bssid,
                f"{_signal_bar(n.signal_dbm)} {n.signal_dbm} dBm",
                str(n.channel),
                str(n.frequency_mhz) if n.frequency_mhz else "—",
                n.security,
                n.mode,
            )

        console.print(table)

    asyncio.run(_scan())


@network_group.command(name="ap")
@click.argument("action", type=click.Choice(["start", "stop", "status", "config"]))
@click.option("--ssid", default="Atlas-OS", help="Access Point SSID")
@click.option("--password", default=None, help="AP password (WPA2)")
@click.option("--channel", default=6, type=int, help="Wi-Fi channel (1-13)")
@click.option("--interface", "-i", default="ap0", help="AP interface name")
@click.pass_context
def network_ap(ctx: click.Context, action: str, ssid: str, password: str | None, channel: int, interface: str) -> None:
    """Manage Access Point mode (Linux with hostapd/dnsmasq)."""
    system = platform.system().lower()
    if system != "linux":
        console.print("[red]Access Point management currently only supported on Linux.[/]")
        return

    if action == "status":
        _show_ap_status(interface)
    elif action == "config":
        _generate_ap_config(ssid, password, channel, interface)
    elif action == "start":
        _start_ap(interface)
    elif action == "stop":
        _stop_ap(interface)


def _show_ap_status(interface: str) -> None:
    """Show AP status."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "hostapd"],
            capture_output=True, text=True, timeout=5
        )
        hostapd_active = result.returncode == 0 and result.stdout.strip() == "active"

        result = subprocess.run(
            ["systemctl", "is-active", "dnsmasq"],
            capture_output=True, text=True, timeout=5
        )
        dnsmasq_active = result.returncode == 0 and result.stdout.strip() == "active"

        table = Table(title="Access Point Status")
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="green")
        table.add_row("hostapd", "[green]active[/]" if hostapd_active else "[red]inactive[/]")
        table.add_row("dnsmasq", "[green]active[/]" if dnsmasq_active else "[red]inactive[/]")
        console.print(table)

        # Show connected clients
        try:
            result = subprocess.run(
                ["hostapd_cli", "-i", interface, "all_sta"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                console.print("\n[cyan]Connected Clients:[/]")
                console.print(result.stdout)
        except Exception:
            pass

    except Exception as exc:
        console.print(f"[red]Failed to get AP status: {exc}[/]")


def _generate_ap_config(ssid: str, password: str | None, channel: int, interface: str) -> None:
    """Generate hostapd/dnsmasq config files."""
    config_dir = Path("/etc/atlas-network")
    config_dir.mkdir(parents=True, exist_ok=True)

    hostapd_conf = config_dir / "hostapd.conf"
    dnsmasq_conf = config_dir / "dnsmasq.conf"

    hostapd_content = f"""interface={interface}
driver=nl80211
ssid={ssid}
hw_mode=g
channel={channel}
wmm_enabled=1
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
"""

    if password:
        hostapd_content += f"""wpa=2
wpa_passphrase={password}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
"""
    else:
        hostapd_content += "wpa=0\n"

    dnsmasq_content = f"""interface={interface}
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
dhcp-option=3,192.168.4.1
dhcp-option=6,192.168.4.1
server=8.8.8.8
server=8.8.4.4
log-queries
log-dhcp
"""

    hostapd_conf.write_text(hostapd_content)
    dnsmasq_conf.write_text(dnsmasq_content)

    console.print("[green]Generated configs:[/]")
    console.print(f"  hostapd: {hostapd_conf}")
    console.print(f"  dnsmasq: {dnsmasq_conf}")
    console.print("[dim]Copy to /etc/hostapd/hostapd.conf and /etc/dnsmasq.conf, "
          "then run 'atlas network ap start'[/]")


def _start_ap(interface: str) -> None:
    """Start Access Point services."""
    config_dir = Path("/etc/atlas-network")
    hostapd_conf = config_dir / "hostapd.conf"
    dnsmasq_conf = config_dir / "dnsmasq.conf"

    if not hostapd_conf.exists() or not dnsmasq_conf.exists():
        console.print("[red]Config files not found. Run 'atlas network ap config' first.[/]")
        return

    try:
        # Copy configs to system locations
        subprocess.run(["cp", str(hostapd_conf), "/etc/hostapd/hostapd.conf"], check=True)
        subprocess.run(["cp", str(dnsmasq_conf), "/etc/dnsmasq.conf"], check=True)

        # Set interface IP
        subprocess.run(["ip", "addr", "add", "192.168.4.1/24", "dev", interface], check=True)
        subprocess.run(["ip", "link", "set", interface, "up"], check=True)

        # Start services
        subprocess.run(["systemctl", "restart", "dnsmasq"], check=True)
        subprocess.run(["systemctl", "restart", "hostapd"], check=True)

        console.print("[green]Access Point started successfully.[/]")
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]Failed to start AP: {exc}[/]")
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/]")


def _stop_ap(interface: str) -> None:
    """Stop Access Point services."""
    try:
        subprocess.run(["systemctl", "stop", "hostapd"], check=True)
        subprocess.run(["systemctl", "stop", "dnsmasq"], check=True)
        subprocess.run(["ip", "link", "set", interface, "down"], check=True)
        console.print("[green]Access Point stopped.[/]")
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]Failed to stop AP: {exc}[/]")
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/]")
