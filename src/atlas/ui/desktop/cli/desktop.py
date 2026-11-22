"""Desktop UI CLI command."""

from __future__ import annotations

import asyncio
import os
import click
from rich.console import Console

# Force Quick Controls 2 style before any Qt imports (Qt 6.5+)
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Material")

console = Console()


@click.command(name="desktop")
@click.option(
    "--url",
    default="http://localhost:8000",
    help="Backend API base URL",
    show_default=True,
)
@click.option(
    "--api-key",
    default=None,
    help="API key for authentication",
)
@click.option(
    "--once",
    is_flag=True,
    help="Fetch data once and exit (for testing without GUI)",
)
@click.option(
    "--no-gui",
    is_flag=True,
    help="Run in console mode without GUI",
)
def desktop_command(url: str, api_key: str | None, once: bool, no_gui: bool):
    """Launch Atlas OS Desktop System Dashboard."""
    if no_gui or once:
        # Console mode - use existing kiosk logic
        console.print("[yellow]Console mode - use 'atlas kiosk start' instead[/]")
        return
    
    # Try to launch Qt GUI
    try:
        from atlas.ui.desktop.main import main
        import os
        
        # Set environment variables for the main() function to read
        os.environ["ATLAS_API_URL"] = url
        if api_key:
            os.environ["ATLAS_API_KEY"] = api_key
        
        console.print(f"[green]Starting Atlas OS Desktop...[/]")
        console.print(f"[cyan]Backend: {url}[/]")
        
        exit_code = main()
        
        if exit_code != 0:
            console.print(f"[red]Desktop exited with code {exit_code}[/]")
        
    except ImportError as e:
        console.print(f"[red]Error: PySide6 not installed[/]")
        console.print(f"[yellow]Install with: pip install PySide6[/]")
        console.print(f"[dim]Import error: {e}[/]")
    except Exception as e:
        console.print(f"[red]Error launching desktop: {e}[/]")


# Also add a simple status command
@click.command(name="status")
@click.option(
    "--url",
    default="http://localhost:8000",
    help="Backend API base URL",
    show_default=True,
)
@click.option(
    "--api-key",
    default=None,
    help="API key for authentication",
)
def desktop_status_command(url: str, api_key: str | None):
    """Check desktop backend connection status."""
    from atlas.ui.kiosk import create_kiosk_controllers
    
    async def check():
        dashboard = await create_kiosk_controllers(url, api_key)
        async with dashboard:
            data = await dashboard.refresh_all()
            
            system = data["system"]
            models = data["models"]
            providers = data["providers"]
            sessions = data["sessions"]
            
            console.print(f"\n[bold]Backend Status:[/] {url}")
            console.print(f"[bold]System:[/] {system.status if not system.error else 'Error: ' + system.error}")
            
            if system.error:
                console.print(f"[red]  Error: {system.error}[/]")
            else:
                console.print(f"  CPU: {system.cpu_usage:.1f}%")
                console.print(f"  Memory: {system.memory_usage:.1f}%")
                console.print(f"  Uptime: {system.uptime}")
            
            console.print(f"\n[bold]Models:[/] {models.total_count} total, {models.loaded_count} loaded")
            if models.error:
                console.print(f"[red]  Error: {models.error}[/]")
            
            console.print(f"\n[bold]Providers:[/] {len(providers)} configured")
            for p in providers:
                status_color = {
                    "healthy": "green",
                    "degraded": "yellow",
                    "unhealthy": "red",
                    "unloaded": "dim",
                }.get(p.status.value, "white")
                console.print(f"  [{status_color}]{p.name}: {p.status.value}[/] ({p.models_count} models)")
            
            console.print(f"\n[bold]Sessions:[/] {len(sessions)} active")
    
    asyncio.run(check())


# Group command
@click.group(name="desktop")
def desktop_group():
    """Atlas OS Desktop commands."""
    pass


desktop_group.add_command(desktop_command, "start")
desktop_group.add_command(desktop_status_command, "status")

# Export for main.py registration
__all__ = ["desktop_group", "desktop_command", "desktop_status_command"]