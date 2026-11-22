"""Network management commands (stub for Phase 5)."""

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group(name="network")
def network_group():
    """Manage network configuration."""
    pass


@network_group.command(name="status")
def network_status():
    """Show network status."""
    console.print("[yellow]Network management coming in Phase 5.[/]")
    table = Table(title="Network Status (Preview)")
    table.add_column("Interface", style="cyan")
    table.add_column("Mode", style="green")
    table.add_column("SSID", style="yellow")
    table.add_column("IP", style="white")
    table.add_row("wlan0", "Client", "MyWiFi", "192.168.1.100")
    table.add_row("ap0", "Access Point", "Atlas-OS", "192.168.4.1")
    console.print(table)


@network_group.command(name="scan")
def network_scan():
    """Scan for available Wi-Fi networks."""
    console.print("[yellow]Scanning for Wi-Fi networks...[/]")
    console.print("[dim]This feature will be available in Phase 5.[/]")
