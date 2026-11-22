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
            "+" if sys.version_info >= (3, 12) else "~",
        )
    )

    # OS
    results.append(("OS", platform.platform(), "+"))

    # Check if runtime health monitor is accessible and has a latest report
    try:
        health = container.resolve("health_monitor")
        # HealthMonitor.latest_report is always available after start().
        # status is a HealthStatus enum: "healthy" | "degraded" | "unhealthy" | "unknown"
        report = health.latest_report
        status_val = report.status.value
        if status_val == "healthy":
            results.append(("Runtime Health", "Healthy", "+"))
        elif status_val == "degraded":
            results.append(("Runtime Health", "Degraded", "~"))
        else:
            results.append(("Runtime Health", status_val.title(), "-"))
    except Exception:
        results.append(("Runtime Health", "Not available", "-"))

    # Check config — AtlasConfig is a Pydantic BaseSettings model; if it
    # loaded without raising a ValidationError it is valid by definition.
    try:
        config = container.resolve("config")
        if config is not None:
            results.append(("Configuration", "Valid (Pydantic validated)", "+"))
        else:
            results.append(("Configuration", "Not loaded", "-"))
    except Exception:
        results.append(("Configuration", "Not loaded", "-"))

    # Check model directory — config.models_dir is a plain str attribute.
    import os

    try:
        config = container.resolve("config")
        models_dir = config.models_dir if config else "models/"
        if os.path.isdir(models_dir):
            count = len([f for f in os.listdir(models_dir) if f.endswith(".gguf")])
            results.append(
                (
                    "Models Directory",
                    f"{models_dir} ({count} GGUF files)",
                    "+" if count > 0 else "~",
                )
            )
        else:
            results.append(("Models Directory", f"{models_dir} — not found", "-"))
    except Exception:
        results.append(("Models Directory", "Check failed", "-"))

    # Check llama-cpp-python installation
    try:
        import llama_cpp  # noqa: F401

        results.append(("llama-cpp-python", "Installed", "+"))
    except ImportError:
        results.append(("llama-cpp-python", "NOT installed — run: pip install llama-cpp-python", "-"))

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
                    f"[bold red]- {errors} critical issue(s) found![/]",
                    border_style="red",
                )
            )
        else:
            console.print(
                Panel(
                    f"[bold yellow]~ {warnings} warning(s) found.[/]",
                    border_style="yellow",
                )
            )
