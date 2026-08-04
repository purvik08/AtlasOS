"""System-level commands."""

import code

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.command()
@click.option("--tail", is_flag=True, help="Stream logs in real-time")
@click.option("--level", default="INFO", help="Filter by log level")
@click.pass_context
def logs(ctx, tail, level):
    """Display or stream runtime logs."""
    if tail:
        console.print("[yellow]Streaming logs... (Ctrl+C to stop)[/]")
        # In practice, we'd subscribe to a log queue; for now we show a sample
        # We'll implement a simple file tail later.
        try:
            with open("atlas.log") as f:
                for line in f:
                    if level.upper() in line:
                        console.print(line.strip())
        except FileNotFoundError:
            console.print("[red]Log file not found.[/]")
    else:
        # Show last 50 lines
        try:
            with open("atlas.log") as f:
                lines = f.readlines()[-50:]
                for line in lines:
                    console.print(line.strip())
        except FileNotFoundError:
            console.print("[red]Log file not found.[/]")


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
