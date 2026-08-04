"""Runtime management commands."""
import asyncio
import sys

import click
import psutil
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@click.group(name="runtime")
def runtime_group():
    """Manage the Atlas OS runtime."""
    pass


@runtime_group.command()
@click.pass_context
def status(ctx):
    """Show runtime status, health, and resource usage."""
    container = ctx.obj["container"]
    health = container.resolve("health_monitor")
    heartbeat = container.resolve("heartbeat_service")
    task_mgr = container.resolve("task_manager")
    registry = container.resolve("service_registry")
    lifecycle = container.resolve("lifecycle_manager")

    # Build status table
    table = Table(title="Atlas OS Runtime Status", box=box.ROUNDED)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    state = lifecycle.state
    app = ctx.obj["app"]
    table.add_row("State", state.value)
    table.add_row("Uptime", f"{app.uptime_seconds:.1f}s")
    table.add_row(
        "Registered Services", str(len(registry.all()) if registry else 0)
    )
    active_count = sum(1 for t in task_mgr._tasks.values() if t.task is not None and not t.task.done()) if task_mgr else 0
    table.add_row(
        "Active Background Tasks", str(active_count)
    )

    # System resources
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    table.add_row("CPU Usage", f"{cpu}%")
    table.add_row(
        "RAM Used", f"{mem.used / (1024**3):.1f} GiB / {mem.total / (1024**3):.1f} GiB"
    )
    table.add_row("RAM Percent", f"{mem.percent}%")

    console.print(table)

    # Health summary
    if health:
        healthy = health.is_healthy()
        panel = Panel(
            (
                "[bold green][+][/] System is healthy"
                if healthy
                else "[bold red][x][/] System is unhealthy"
            ),
            state="green" if healthy else "red",
            border_style="green" if healthy else "red",
        )
        console.print(panel)


@runtime_group.command()
@click.pass_context
def stop(ctx):
    """Gracefully shut down Atlas OS."""
    app = ctx.obj["app"]
    console.print("[yellow]Shutting down Atlas OS...[/]")

    asyncio.run(app.stop())
    console.print("[green][+] Shutdown complete.[/]")
    sys.exit(0)


@runtime_group.command()
@click.pass_context
def restart(ctx):
    """Restart the Atlas OS runtime."""
    app = ctx.obj["app"]
    console.print("[yellow]Restarting Atlas OS...[/]")

    asyncio.run(app.stop())
    asyncio.run(app.start())
    console.print("[green][+] Restart complete.[/]")


@runtime_group.command()
@click.pass_context
def health(ctx):
    """Display detailed health checks for all services."""
    container = ctx.obj["container"]
    health = container.resolve("health_monitor")
    if not health:
        console.print("[red]Health monitor not available.[/]")
        return

    results = health.run_all_checks()
    table = Table(title="Service Health")
    table.add_column("Service", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Message", style="white")

    for svc, result in results.items():
        status_icon = "[+]" if result.ok else "[x]"
        status_color = "green" if result.ok else "red"
        table.add_row(svc, f"[{status_color}]{status_icon}[/]", result.message or "")
    console.print(table)


@runtime_group.command()
@click.pass_context
def services(ctx):
    """List all registered services and their state."""
    container = ctx.obj["container"]
    registry = container.resolve("service_registry")
    if not registry:
        console.print("[red]Service registry not available.[/]")
        return

    services_dict = {s.name: s for s in registry.all()}
    table = Table(title="Registered Services")
    table.add_column("Name", style="cyan")
    table.add_column("State", style="green")
    for name, svc in services_dict.items():
        state = getattr(svc, "state", "unknown")
        table.add_row(name, state)
    console.print(table)