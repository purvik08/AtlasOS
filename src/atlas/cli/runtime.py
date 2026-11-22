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
    health_monitor = container.resolve("health_monitor")
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

    # ServiceRegistry.all() returns a tuple of IService objects.
    registered_count = len(registry.all()) if registry else 0
    table.add_row("Registered Services", str(registered_count))

    # Count active (not-done) background tasks.
    active_count = (
        sum(
            1
            for s in task_mgr._tasks.values()
            if s.task is not None and not s.task.done()
        )
        if task_mgr
        else 0
    )
    table.add_row("Active Background Tasks", str(active_count))

    # System resources via psutil.
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    table.add_row("CPU Usage", f"{cpu}%")
    table.add_row(
        "RAM Used",
        f"{mem.used / (1024**3):.1f} GiB / {mem.total / (1024**3):.1f} GiB",
    )
    table.add_row("RAM Percent", f"{mem.percent}%")

    console.print(table)

    # Health summary — read from the cached HealthMonitor report (non-blocking).
    if health_monitor:
        report = health_monitor.latest_report
        is_healthy = report.status.value == "healthy"
        panel = Panel(
            (
                "[bold green][+][/] System is healthy"
                if is_healthy
                else f"[bold red][x][/] System is {report.status.value}"
            ),
            border_style="green" if is_healthy else "red",
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
    health_monitor = container.resolve("health_monitor")
    if not health_monitor:
        console.print("[red]Health monitor not available.[/]")
        return

    # Read from the cached report — no live round-trip needed.
    report = health_monitor.latest_report

    table = Table(title="Service Health", box=box.ROUNDED)
    table.add_column("Service", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Message", style="white")

    for svc_health in report.services:
        is_ok = svc_health.status.value == "healthy"
        status_icon = "[green][+][/]" if is_ok else "[red][x][/]"
        table.add_row(svc_health.name, status_icon, svc_health.message or "")

    console.print(table)
    console.print(
        f"\n[dim]Report generated at: {report.generated_at:.0f} "
        f"(overall: {report.status.value})[/]"
    )


@runtime_group.command()
@click.pass_context
def services(ctx):
    """List all registered services and their state."""
    container = ctx.obj["container"]
    registry = container.resolve("service_registry")
    if not registry:
        console.print("[red]Service registry not available.[/]")
        return

    # ServiceRegistry.all() returns a tuple of IService objects.
    all_services = registry.all()
    table = Table(title="Registered Services", box=box.ROUNDED)
    table.add_column("Name", style="cyan")
    table.add_column("Dependencies", style="dim")
    for svc in all_services:
        deps = ", ".join(svc.dependencies) if svc.dependencies else "none"
        table.add_row(svc.name, deps)
    console.print(table)
