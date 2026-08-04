"""Voice management commands (stub for Phase 5)."""

import click
from rich.console import Console

console = Console()


@click.group(name="voice")
def voice_group():
    """Manage voice interaction features."""
    pass


@voice_group.command(name="status")
def voice_status():
    """Show voice system status."""
    console.print("[yellow]Voice management coming in Phase 5.[/]")
    console.print("Components:")
    console.print("  • Wake Word: [dim]not configured[/]")
    console.print("  • Speech-to-Text: [dim]not configured[/]")
    console.print("  • Text-to-Speech: [dim]not configured[/]")
