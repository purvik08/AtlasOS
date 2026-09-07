"""System-level commands."""

from __future__ import annotations

import code
import logging
import logging.handlers
import signal
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table

console = Console()


def _get_log_file() -> Path:
    """Get the Atlas OS log file path."""
    # Check for running app config
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    return log_dir / "atlas.log"


def _setup_file_logging() -> None:
    """Set up file logging with rotation."""
    log_file = _get_log_file()
    handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root = logging.getLogger()
    if not any(isinstance(h, logging.handlers.RotatingFileHandler) for h in root.handlers):
        root.addHandler(handler)


def _tail_file(
    path: Path,
    lines: int = 50,
    follow: bool = False,
    level_filter: str | None = None,
) -> Iterator[str]:
    """Tail a file, optionally following new lines."""
    level_filter = level_filter.upper() if level_filter else None

    def should_include(line: str) -> bool:
        if not level_filter:
            return True
        return f"| {level_filter} |" in line or f"| {level_filter.lower()} |" in line

    if not path.exists():
        yield f"[red]Log file not found: {path}[/]"
        return

    with path.open("r", encoding="utf-8", errors="replace") as f:
        # Get last N lines
        all_lines = f.readlines()
        for line in all_lines[-lines:]:
            if should_include(line):
                yield line.rstrip()

        if not follow:
            return

        # Follow new lines
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue
            if should_include(line):
                yield line.rstrip()


@click.command(name="logs")
@click.option("--tail", "-t", is_flag=True, help="Stream logs in real-time (follow)")
@click.option("--lines", "-n", default=50, type=int, help="Number of lines to show")
@click.option("--level", default=None, help="Filter by log level (DEBUG, INFO, WARNING, ERROR)")
@click.option(
    "--file",
    "log_file",
    default=None,
    type=click.Path(exists=True, path_type=Path),
    help="Log file to read",
)
@click.pass_context
def logs(ctx: click.Context, tail: bool, lines: int, level: str | None, log_file: Path | None) -> None:
    """Display or stream runtime logs."""
    _setup_file_logging()

    target_file = log_file or _get_log_file()

    if tail:
        console.print(f"[cyan]Streaming logs from {target_file}... (Ctrl+C to stop)[/]")

        def signal_handler(signum: int, frame: Any) -> None:
            console.print("\n[dim]Stopped.[/]")
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)

        try:
            for line in _tail_file(target_file, lines=lines, follow=True, level_filter=level):
                # Colorize log levels
                if "| ERROR |" in line:
                    console.print(f"[red]{line}[/]")
                elif "| WARNING |" in line:
                    console.print(f"[yellow]{line}[/]")
                elif "| DEBUG |" in line:
                    console.print(f"[dim]{line}[/]")
                else:
                    console.print(line)
        except KeyboardInterrupt:
            console.print("\n[dim]Stopped.[/]")
    else:
        # Show last N lines
        try:
            for line in _tail_file(target_file, lines=lines, follow=False, level_filter=level):
                if "| ERROR |" in line:
                    console.print(f"[red]{line}[/]")
                elif "| WARNING |" in line:
                    console.print(f"[yellow]{line}[/]")
                elif "| DEBUG |" in line:
                    console.print(f"[dim]{line}[/]")
                else:
                    console.print(line)
        except FileNotFoundError:
            console.print("[red]Log file not found.[/]")


@click.command(name="log-rotate")
@click.pass_context
def log_rotate(ctx: click.Context) -> None:
    """Force log rotation."""
    _setup_file_logging()
    _get_log_file()

    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.handlers.RotatingFileHandler):
            handler.doRollover()
            console.print(f"[green]Log rotated: {handler.baseFilename}[/]")
            return

    console.print("[yellow]No rotating file handler found.[/]")


@click.command()
@click.pass_context
def shell(ctx: click.Context) -> None:
    """Launch an interactive Python shell with the runtime container."""
    container = ctx.obj["container"]
    banner = "Atlas OS Shell – container available as `container`"
    code.interact(local={"container": container}, banner=banner)


@click.command(name="runtime")
@click.pass_context
def runtime_info(ctx: click.Context) -> None:
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
    tasks: list[dict[str, Any]] = []
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
@click.option("--check-only", is_flag=True, help="Only check for updates, don't install")
@click.option("--prerelease", is_flag=True, help="Include pre-release versions")
@click.option("--repo", default="atlas-os/atlas-os", help="GitHub repository (owner/repo)")
@click.pass_context
def update(ctx: click.Context, check_only: bool, prerelease: bool, repo: str) -> None:
    """Update Atlas OS to the latest version from GitHub releases."""
    from atlas.update.core import UpdateManager

    app = ctx.obj["app"]
    current_version = getattr(app, "__version__", "0.1.0")

    manager = UpdateManager(repo=repo, current_version=current_version)

    async def _update() -> None:
        console.print("[cyan]Checking for updates...[/]")
        release = await manager.check_for_updates(include_prerelease=prerelease)

        if not release:
            console.print(f"[green]No updates available (current: {current_version})[/]")
            return

        console.print(f"[yellow]Update available: {current_version} -> {release.version}[/]")
        if len(release.body) > 300:
            body = f"[dim]{release.body[:300]}...[/]"
        else:
            body = f"[dim]{release.body}[/]"
        console.print(body)

        if check_only:
            console.print("[dim]Check only mode - not installing.[/]")
            return

        console.print("[cyan]Downloading release...[/]")
        try:
            asset_path = await manager.download_release(release)
        except Exception as exc:
            console.print(f"[red]Download failed: {exc}[/]")
            return

        console.print("[cyan]Installing...[/]")
        success = manager.install_release(asset_path)

        if success:
            msg = f"Update complete! Restart Atlas OS to use version {release.version}"
            console.print(f"[green][+] {msg}[/]")
        else:
            console.print("[red]Update failed.[/]")

    import asyncio
    asyncio.run(_update())


@click.command()
@click.option("--version", default=None, help="Specific version to install (e.g., 0.2.0)")
@click.option("--repo", default="atlas-os/atlas-os", help="GitHub repository")
@click.pass_context
def install(ctx: click.Context, version: str | None, repo: str) -> None:
    """Install a specific version of Atlas OS."""
    from atlas.update.core import download_and_install

    app = ctx.obj["app"]
    current_version = getattr(app, "__version__", "0.1.0")

    async def _install() -> None:
        console.print(f"[cyan]Installing Atlas OS {version or 'latest'}...[/]")
        success = await download_and_install(repo, current_version, version)
        if success:
            console.print("[green][+] Installation complete![/]")
        else:
            console.print("[red]Installation failed.[/]")

    import asyncio
    asyncio.run(_install())
