"""Main CLI entry point for Atlas OS."""

import asyncio
from pathlib import Path

import click
from rich.console import Console

from atlas.cli.ai import chat_command, provider_group, session_group
from atlas.cli.apikey import apikey_group
from atlas.cli.config import config_group
from atlas.cli.doctor import doctor
from atlas.cli.memory import memory_group
from atlas.cli.models import models_group
from atlas.cli.network import network_group
from atlas.cli.plugins import plugins_group
from atlas.cli.rag import rag_group
from atlas.cli.runtime import runtime_group
from atlas.cli.system import log_rotate, logs, runtime_info, shell, update
from atlas.cli.voice import voice_group
from atlas.cli.process_manager import run_atlas_start
from atlas.config.loader import load_config
from atlas.runtime.application import AtlasApplication
from atlas.ui.dashboard.cli.dashboard import dashboard_group

console = Console()


class LazyCLIContext(dict):
    """Dictionary-compatible context for Click that lazily instantiates AtlasApplication.

    Fast commands (e.g. atlas --help, atlas version, atlas start) execute immediately
    without loading heavy AI models or background runtime dependencies.
    """

    def __init__(self, config_path: Path | str = "configs/atlas.yaml") -> None:
        super().__init__()
        self._config_path = Path(config_path)
        self["config_path"] = self._config_path
        self._app = None

    def _ensure_app(self) -> AtlasApplication:
        if self._app is None:
            config = load_config(self._config_path)
            self._app = AtlasApplication(config)
            # Register core services in the container for CLI access
            self._app.container.register_instance("health_monitor", self._app.health_monitor)
            self._app.container.register_instance("heartbeat_service", self._app.heartbeat)
            self._app.container.register_instance("task_manager", self._app.tasks)
            self._app.container.register_instance("service_registry", self._app.registry)
            self._app.container.register_instance("lifecycle_manager", self._app._lifecycle)
            self._app.container.register_instance("config", self._app.config)
            self["app"] = self._app
            self["container"] = self._app.container
        return self._app

    def __getitem__(self, key):
        if key in ("app", "container") and key not in self:
            self._ensure_app()
        return super().__getitem__(key)

    def get(self, key, default=None):
        if key in ("app", "container") and key not in self:
            self._ensure_app()
        return super().get(key, default)


@click.group()
@click.pass_context
def cli(ctx):
    """Atlas OS – AI Edge Operating System CLI.

    Atlas OS is a modular, offline-first AI Edge Operating System
    designed for Raspberry Pi 5 and edge devices.
    """
    if ctx.obj is None:
        ctx.obj = LazyCLIContext(config_path="configs/atlas.yaml")
    elif not isinstance(ctx.obj, LazyCLIContext) and "app" not in ctx.obj:
        lazy_ctx = LazyCLIContext(config_path=ctx.obj.get("config_path", "configs/atlas.yaml"))
        lazy_ctx.update(ctx.obj)
        ctx.obj = lazy_ctx


# ============================================================
# Register all commands
# ============================================================
cli.add_command(config_group)
cli.add_command(logs)
cli.add_command(log_rotate)
cli.add_command(shell)
cli.add_command(runtime_info)
cli.add_command(update)
cli.add_command(models_group)
cli.add_command(network_group)
cli.add_command(voice_group)
cli.add_command(plugins_group)
cli.add_command(runtime_group)
cli.add_command(doctor)
cli.add_command(apikey_group)
cli.add_command(dashboard_group)
cli.add_command(memory_group)
cli.add_command(rag_group)
# Phase 5: AI Engine
cli.add_command(chat_command)
cli.add_command(provider_group)
cli.add_command(session_group)


# ============================================================
# Core commands (moved from legacy)
# ============================================================
@cli.command()
@click.option("--url", default="http://127.0.0.1:8000", help="Backend API base URL", show_default=True)
@click.option("--api-key", default=None, help="API key for authentication")
@click.option("--no-gui", is_flag=True, help="Run in console mode without GUI")
@click.option("--once", is_flag=True, help="Fetch data once and exit (for testing without GUI)")
@click.pass_context
def start(ctx, url: str, api_key: str | None, no_gui: bool, once: bool):
    """Start the Atlas OS runtime (backend + desktop)."""
    from atlas.cli.process_manager import run_atlas_start
    console.print("[green]Starting Atlas OS...[/]")
    asyncio.run(run_atlas_start(url=url, api_key=api_key, no_gui=no_gui, once=once))
    console.print("[green][+] Atlas OS stopped.[/]")


@cli.command()
def version():
    """Display Atlas OS version."""
    try:
        from atlas import __version__

        console.print(f"[bold]Atlas OS[/] version [cyan]{__version__}[/]")
    except ImportError:
        console.print("[bold]Atlas OS[/] version [yellow]unknown[/]")