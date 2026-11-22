"""Kiosk UI CLI commands."""

from __future__ import annotations

import asyncio

import click
from rich.console import Console
from rich.table import Table

from atlas.ui.kiosk import (
    KioskDashboard,
    SystemController,
    ModelController,
    ProviderController,
    SessionController,
    create_kiosk_controllers,
)

console = Console()


@click.group(name="kiosk")
def kiosk_group():
    """Kiosk UI commands - real backend integration."""
    pass


@kiosk_group.command()
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
    "--interval",
    type=int,
    default=5,
    help="Refresh interval in seconds",
    show_default=True,
)
@click.option(
    "--once",
    is_flag=True,
    help="Fetch once and exit (no live refresh)",
)
@click.pass_context
def start(ctx, url: str, api_key: str | None, interval: int, once: bool):
    """Start kiosk dashboard with real backend data."""
    asyncio.run(_run_kiosk(url, api_key, interval, once))


async def _run_kiosk(url: str, api_key: str | None, interval: int, once: bool):
    """Run the kiosk dashboard loop."""
    dashboard = await create_kiosk_controllers(url, api_key)
    async with dashboard:
        console.print(f"[green]Connecting to backend at {url}...[/]")

        if once:
            await _display_dashboard(dashboard)
            return

        console.print(f"[cyan]Starting live refresh (every {interval}s). Press Ctrl+C to stop.[/]")
        try:
            while True:
                await _display_dashboard(dashboard)
                await asyncio.sleep(interval)
        except KeyboardInterrupt:
            console.print("\n[yellow]Kiosk stopped.[/]")


async def _display_dashboard(dashboard: KioskDashboard):
    """Display full dashboard."""
    data = await dashboard.refresh_all()

    system = data["system"]
    models = data["models"]
    providers = data["providers"]
    sessions = data["sessions"]

    # System info
    console.print("\n[bold blue]=== SYSTEM ====[/]")
    if system.error:
        console.print(f"[red]Error: {system.error}[/]")
    else:
        console.print(f"Status: [green]{system.status}[/]")
        console.print(f"CPU: {system.cpu_usage:.1f}%")
        console.print(f"Memory: {system.memory_usage:.1f}%")
        console.print(f"Uptime: {system.uptime}")

    # Models
    console.print("\n[bold blue]=== MODELS ====[/]")
    if models.error:
        console.print(f"[red]Error: {models.error}[/]")
    else:
        console.print(f"Total: {models.total_count} | Loaded: {models.loaded_count}")
        if models.models:
            table = Table(show_header=True, header_style="bold")
            table.add_column("Name")
            table.add_column("Provider")
            table.add_column("Size (GB)")
            table.add_column("Quantization")
            table.add_column("Loaded")
            for m in models.models[:20]:
                table.add_row(
                    m.name,
                    m.provider,
                    f"{m.size_gb:.2f}",
                    m.quantization,
                    "Yes" if m.loaded else "No",
                )
            console.print(table)
        else:
            console.print("[yellow]No models found[/]")

    # Providers
    console.print("\n[bold blue]=== PROVIDERS ===[/]")
    if providers:
        table = Table(show_header=True, header_style="bold")
        table.add_column("Name")
        table.add_column("Status")
        table.add_column("Models")
        table.add_column("Last Check")
        for p in providers:
            status_color = {
                "healthy": "green",
                "degraded": "yellow",
                "unhealthy": "red",
                "unloaded": "dim",
            }.get(p.status.value, "white")
            table.add_row(
                p.name,
                f"[{status_color}]{p.status.value}[/]",
                str(p.models_count),
                p.last_check.strftime("%H:%M:%S"),
            )
        console.print(table)
    else:
        console.print("[yellow]No providers found[/]")

    # Sessions
    console.print("\n[bold blue]=== SESSIONS ===[/]")
    console.print(f"Active: {data['session_count']}")
    if sessions:
        table = Table(show_header=True, header_style="bold")
        table.add_column("ID")
        table.add_column("Provider")
        table.add_column("Model")
        table.add_column("Role")
        table.add_column("Messages")
        table.add_column("Created")
        for s in sessions[:10]:
            table.add_row(
                s.id[:8] + "...",
                s.provider,
                s.model,
                s.role or "-",
                str(s.message_count),
                s.created_at.strftime("%H:%M:%S"),
            )
        console.print(table)
    else:
        console.print("[yellow]No active sessions[/]")

    console.print("\n[dim]Press Ctrl+C to stop live refresh[/]")


@kiosk_group.command()
@click.option("--url", default="http://localhost:8000", help="Backend API base URL")
@click.option("--api-key", default=None, help="API key for authentication")
@click.pass_context
def system(ctx, url: str, api_key: str | None):
    """Show system info."""
    asyncio.run(_run_system(url, api_key))


async def _run_system(url: str, api_key: str | None):
    """Fetch and display system info."""
    async with SystemController(url, api_key) as ctrl:
        info = await ctrl.update()
        if info.error:
            console.print(f"[red]Error: {info.error}[/]")
        else:
            console.print(f"[bold]System Status:[/] {info.status}")
            console.print(f"[bold]CPU:[/] {info.cpu_usage:.1f}%")
            console.print(f"[bold]Memory:[/] {info.memory_usage:.1f}%")
            console.print(f"[bold]Uptime:[/] {info.uptime}")


@kiosk_group.command()
@click.option("--url", default="http://localhost:8000", help="Backend API base URL")
@click.option("--api-key", default=None, help="API key for authentication")
@click.option("--provider", default=None, help="Filter by provider")
@click.pass_context
def models(ctx, url: str, api_key: str | None, provider: str | None):
    """Show model registry."""
    asyncio.run(_run_models(url, api_key, provider))


async def _run_models(url: str, api_key: str | None, provider: str | None):
    """Fetch and display model registry."""
    async with ModelController(url, api_key) as ctrl:
        registry = await ctrl.refresh(provider=provider)
        if registry.error:
            console.print(f"[red]Error: {registry.error}[/]")
        else:
            console.print(f"[bold]Models:[/] Total={registry.total_count} Loaded={registry.loaded_count}")
            if registry.models:
                table = Table(show_header=True, header_style="bold")
                table.add_column("Name")
                table.add_column("Provider")
                table.add_column("Size (GB)")
                table.add_column("Quantization")
                table.add_column("Loaded")
                for m in registry.models:
                    table.add_row(
                        m.name,
                        m.provider,
                        f"{m.size_gb:.2f}",
                        m.quantization,
                        "✓" if m.loaded else "✗",
                    )
                console.print(table)
            else:
                console.print("[yellow]No models found[/]")


@kiosk_group.command()
@click.option("--url", default="http://localhost:8000", help="Backend API base URL")
@click.option("--api-key", default=None, help="API key for authentication")
@click.pass_context
def providers(ctx, url: str, api_key: str | None):
    """Show provider health."""
    asyncio.run(_run_providers(url, api_key))


async def _run_providers(url: str, api_key: str | None):
    """Fetch and display provider health."""
    async with ProviderController(url, api_key) as ctrl:
        provider_list = await ctrl.list_providers()
        if not provider_list:
            console.print("[yellow]No providers found[/]")
            return

        health_list = await ctrl.check_all([p.get("name", "") for p in provider_list if p.get("name")])

        table = Table(show_header=True, header_style="bold")
        table.add_column("Name")
        table.add_column("Status")
        table.add_column("Models")
        table.add_column("Last Check")
        for p in health_list:
            status_color = {
                "healthy": "green",
                "degraded": "yellow",
                "unhealthy": "red",
                "unloaded": "dim",
            }.get(p.status.value, "white")
            table.add_row(
                p.name,
                f"[{status_color}]{p.status.value}[/]",
                str(p.models_count),
                p.last_check.strftime("%H:%M:%S"),
            )
        console.print(table)


@kiosk_group.command()
@click.option("--url", default="http://localhost:8000", help="Backend API base URL")
@click.option("--api-key", default=None, help="API key for authentication")
@click.pass_context
def sessions(ctx, url: str, api_key: str | None):
    """Show active chat sessions."""
    asyncio.run(_run_sessions(url, api_key))


async def _run_sessions(url: str, api_key: str | None):
    """Fetch and display chat sessions."""
    async with SessionController(url, api_key) as ctrl:
        sessions = await ctrl.list()
        console.print(f"[bold]Active Sessions:[/] {len(sessions)}")
        if sessions:
            table = Table(show_header=True, header_style="bold")
            table.add_column("ID")
            table.add_column("Provider")
            table.add_column("Model")
            table.add_column("Role")
            table.add_column("Messages")
            table.add_column("Created")
            for s in sessions:
                table.add_row(
                    s.id[:8] + "...",
                    s.provider,
                    s.model,
                    s.role or "-",
                    str(s.message_count),
                    s.created_at.strftime("%H:%M:%S"),
                )
            console.print(table)
        else:
            console.print("[yellow]No active sessions[/]")