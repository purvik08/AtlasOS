"""Diagnostic checks for Atlas OS."""

import platform
import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.box import SIMPLE

console = Console()


@click.command()
@click.pass_context
def doctor(ctx):
    """Run comprehensive system diagnostics."""
    container = ctx.obj["container"]
    results = []

    # Python version
    results.append(
        (
            "Python",
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "+" if sys.version_info >= (3, 14) else "~",
        )
    )

    # OS
    results.append(("OS", platform.platform(), "+"))

    # Check if runtime is healthy
    try:
        health = container.resolve("health_monitor")
        if health and health.is_healthy():
            results.append(("Runtime Health", "Healthy", "+"))
        else:
            results.append(("Runtime Health", "Unhealthy", "-"))
    except Exception:
        results.append(("Runtime Health", "Not available", "-"))

    # Check config
    try:
        config = container.resolve("config")
        errors = config.validate() if config else []
        if errors == []:
            results.append(("Configuration", "Valid", "+"))
        else:
            results.append(("Configuration", f"{len(errors)} errors", "-"))
    except Exception:
        results.append(("Configuration", "Not loaded", "-"))

    # Check model directory
    import os

    try:
        config = container.resolve("config")
        models_dir = config.get("models_dir", "models/") if config else "models/"
        if os.path.isdir(models_dir):
            count = len([f for f in os.listdir(models_dir) if f.endswith('.gguf')])
            results.append(
                (
                    "Models Directory",
                    f"{models_dir} ({count} GGUF files)",
                    "+" if count > 0 else "~",
                )
            )
        else:
            results.append(("Models Directory", "Not found", "-"))
    except Exception:
        results.append(("Models Directory", "Check failed", "-"))

    # Build table
    table = Table(title="Atlas OS Doctor", box=SIMPLE)
    table.add_column("Check", style="cyan")
    table.add_column("Result", style="white")
    table.add_column("Status", style="green")
    for name, value, status in results:
        table.add_row(name, value, status)
    console.print(table)

    # Overall status
    all_ok = all(status == "+" for _, _, status in results)
    if all_ok:
        console.print(Panel("[bold green]+ All systems go![/]", border_style="green"))
    else:
        warnings = sum(1 for _, _, status in results if status == "~")
        errors = sum(1 for _, _, status in results if status == "-")
        if errors > 0:
            console.print(
                Panel(
                    f"[bold red]- {errors} critical issues found![/]",
                    border_style="red",
                )
            )
        else:
            console.print(
                Panel(
                    f"[bold yellow]~ {warnings} warnings found.[/]",
                    border_style="yellow",
                )
            )