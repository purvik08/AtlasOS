"""Atlas OS Dashboard CLI commands.

Unified CLI for both Desktop and Kiosk modes of the Dashboard UI.
"""

from __future__ import annotations

import asyncio
import os
import subprocess

import click
from rich.console import Console

console = Console()


@click.command(name="dashboard")
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
    "--kiosk",
    is_flag=True,
    help="Run in kiosk mode (touch-optimized, fullscreen)",
)
@click.option(
    "--fullscreen",
    is_flag=True,
    help="Run in fullscreen mode (kiosk mode)",
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
def dashboard_command(
    url: str,
    api_key: str | None,
    kiosk: bool,
    fullscreen: bool,
    once: bool,
    no_gui: bool,
):
    """Launch Atlas OS Dashboard (Desktop or Kiosk mode)."""
    
    # Set environment variables
    env = os.environ.copy()
    env["ATLAS_API_URL"] = url
    if api_key:
        env["ATLAS_API_KEY"] = api_key
    if kiosk:
        env["ATLAS_DASHBOARD_KIOSK"] = "1"
    if fullscreen:
        env["ATLAS_DASHBOARD_FULLSCREEN"] = "1"

    if no_gui or once:
        # Console mode - fetch data once and display
        async def _console_mode():
            from atlas.api.sdk import AtlasSDK
            from atlas.ui.dashboard.models import ChatSession, ModelRegistry, SystemInfo

            sdk = AtlasSDK(base_url=url, api_key=api_key)
            async with sdk:
                try:
                    console.print(f"\n[bold]Backend Status:[/] {url}")

                    # System info
                    system = await SystemInfo.fetch(sdk)
                    console.print("[bold]System:[/] OK")
                    console.print(f"  CPU: {system.cpu_percent:.1f}%")
                    console.print(
                        f"  Memory: {system.memory_percent:.1f}% "
                        f"({system.memory_used_gb:.1f}/{system.memory_total_gb:.1f} GB)"
                    )
                    console.print(f"  Disk: {system.disk_percent:.1f}%")
                    console.print(f"  Uptime: {system.uptime_seconds:.0f}s")

                    # Models
                    models = await ModelRegistry.fetch(sdk)
                    loaded_count = sum(1 for m in models.models if m.loaded)
                    console.print(
                        f"\n[bold]Models:[/] {len(models.models)} total, "
                        f"{loaded_count} loaded"
                    )
                    for m in models.models:
                        status = "loaded" if m.loaded else "unloaded"
                        console.print(
                            f"  {m.display_name} ({m.model_id}) - "
                            f"{status} - {m.size_gb:.2f} GB"
                        )

                    # Providers
                    providers = await sdk.list_providers()
                    console.print(f"\n[bold]Providers:[/] {len(providers)} configured")
                    for p in providers:
                        status = "available" if p.get("available") else "offline"
                        status_color = "green" if p.get("available") else "dim"
                        console.print(f"  [{status_color}]{p.get('name')}: {status}[/]")

                    # Sessions
                    sessions = await ChatSession.fetch_all(sdk)
                    console.print(f"\n[bold]Sessions:[/] {len(sessions)} active")
                    for s in sessions[:5]:
                        console.print(
                            f"  {s.session_id[:8]}... - {s.provider_name}/{s.model_id} - "
                            f"{len(s.history)} msgs"
                        )

                except Exception as e:
                    console.print(f"[red]Error connecting to backend: {e}[/]")
                    console.print(
                        "[yellow]Make sure the API server is running: "
                        "python -m atlas.api.server[/]"
                    )

        asyncio.run(_console_mode())
        return

    # Launch Qt GUI
    try:
        console.print("[green]Starting Atlas OS Dashboard...[/]")
        console.print(f"[cyan]Backend: {url}[/]")
        mode = "Kiosk" if kiosk else "Desktop"
        suffix = " (Fullscreen)" if fullscreen else ""
        console.print(f"[cyan]Mode: {mode}{suffix}[/]")

        # Import here to avoid circular imports
        from atlas.utils import get_python_executable
        dashboard_script = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "main.py")
        )
        
        # Launch dashboard in a subprocess with the environment
        proc = subprocess.Popen(
            [get_python_executable(), dashboard_script],
            env=env,
        )

        exit_code = proc.wait()

        if exit_code != 0:
            console.print(f"[red]Dashboard exited with code {exit_code}[/]")

    except ImportError as e:
        console.print("[red]Error: PySide6 not installed[/]")
        console.print("[yellow]Install with: pip install PySide6[/]")
        console.print(f"[dim]Import error: {e}[/]")
    except Exception as e:
        console.print(f"[red]Error launching dashboard: {e}[/]")


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
def dashboard_status_command(url: str, api_key: str | None):
    """Check dashboard backend connection status."""
    from atlas.api.sdk import AtlasSDK
    from atlas.ui.dashboard.models import ChatSession, ModelRegistry, SystemInfo

    async def check():
        sdk = AtlasSDK(base_url=url, api_key=api_key)
        async with sdk:
            try:
                console.print(f"\n[bold]Backend Status:[/] {url}")

                system = await SystemInfo.fetch(sdk)
                console.print("[bold]System:[/] OK")
                console.print(f"  CPU: {system.cpu_percent:.1f}%")
                console.print(
                    f"  Memory: {system.memory_percent:.1f}% "
                    f"({system.memory_used_gb:.1f}/{system.memory_total_gb:.1f} GB)"
                )
                console.print(f"  Disk: {system.disk_percent:.1f}%")

                models = await ModelRegistry.fetch(sdk)
                loaded_count = sum(1 for m in models.models if m.loaded)
                console.print(
                    f"\n[bold]Models:[/] {len(models.models)} total, "
                    f"{loaded_count} loaded"
                )

                providers = await sdk.list_providers()
                console.print(f"\n[bold]Providers:[/] {len(providers)} configured")
                for p in providers:
                    status = "available" if p.get("available") else "offline"
                    status_color = "green" if p.get("available") else "dim"
                    console.print(f"  [{status_color}]{p.get('name')}: {status}[/]")

                sessions = await ChatSession.fetch_all(sdk)
                console.print(f"\n[bold]Sessions:[/] {len(sessions)} active")

            except Exception as e:
                console.print(f"[red]Error: {e}[/]")

    asyncio.run(check())


# Group command
@click.group(name="dashboard")
def dashboard_group():
    """Atlas OS Dashboard commands."""
    pass


dashboard_group.add_command(dashboard_command, "start")
dashboard_group.add_command(dashboard_status_command, "status")

# Export for main.py registration
__all__ = ["dashboard_group", "dashboard_command", "dashboard_status_command"]
