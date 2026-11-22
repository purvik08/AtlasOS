"""System-level commands."""

import code
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()

# Log file location — the logs/ directory is part of the repo structure.
_LOG_FILE = Path("logs/atlas.log")


@click.command()
@click.option("--tail", is_flag=True, help="Stream logs in real-time")
@click.option("--level", default="INFO", help="Filter by log level")
@click.pass_context
def logs(ctx, tail, level):
    """Display or stream runtime logs."""
    if not _LOG_FILE.exists():
        console.print(
            f"[red]Log file not found:[/] {_LOG_FILE}\n"
            "[dim]Atlas OS writes logs to logs/atlas.log when configured with "
            "a FileHandler. Run 'atlas start' first.[/]"
        )
        return

    if tail:
        console.print(f"[yellow]Streaming logs from {_LOG_FILE} … (Ctrl+C to stop)[/]")
        try:
            with open(_LOG_FILE) as f:
                for line in f:
                    if level.upper() in line:
                        console.print(line.strip())
        except OSError as exc:
            console.print(f"[red]Could not read log file:[/] {exc}")
    else:
        # Show last 50 lines
        try:
            with open(_LOG_FILE) as f:
                lines = f.readlines()[-50:]
                for line in lines:
                    console.print(line.strip())
        except OSError as exc:
            console.print(f"[red]Could not read log file:[/] {exc}")


@click.command()
@click.pass_context
def shell(ctx):
    """Launch an interactive Python shell with the runtime container."""
    container = ctx.obj["container"]
    banner = "Atlas OS Shell – container available as `container`"
    code.interact(local={"container": container}, banner=banner)


@click.command(name="runtime")
@click.pass_context
def runtime_info(ctx):
    """Show detailed runtime information (threads, tasks, etc.)."""
    container = ctx.obj["container"]
    task_mgr = container.resolve("task_manager")
    if not task_mgr:
        console.print("[red]Task manager not available.[/]")
        return

    table = Table(title="Background Tasks")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Status", style="yellow")
    tasks = []
    for name, supervised in task_mgr._tasks.items():
        task = supervised.task
        if task is None:
            status = "pending"
        elif task.done():
            if task.cancelled():
                status = "cancelled"
            elif task.exception() is not None:
                status = "failed"
            else:
                status = "finished"
        else:
            status = "running"
        task_id = id(task) if task is not None else None
        tasks.append({"id": task_id, "name": name, "status": status})
    for t in tasks:
        table.add_row(str(t["id"]), t["name"], t["status"])
    console.print(table)


@click.command()
def update():
    """Update Atlas OS to the latest version (placeholder)."""
    console.print("[yellow]Update command not yet implemented.[/]")
