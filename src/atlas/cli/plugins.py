"""Plugin management commands (stub for Phase 6)."""

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group(name="plugins")
def plugins_group():
    """Manage Atlas OS plugins."""
    pass


@plugins_group.command(name="list")
def plugin_list():
    """List installed plugins."""
    console.print("[yellow]Plugin management coming in Phase 6.[/]")
    table = Table(title="Plugins (Preview)")
    table.add_column("Name", style="cyan")
    table.add_column("Version", style="green")
    table.add_column("Status", style="yellow")
    table.add_row("example-plugin", "0.1.0", "disabled")
    console.print(table)
