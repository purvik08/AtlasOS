"""Main CLI entry point for Atlas OS."""

import click
import sys
from pathlib import Path

import asyncio

from atlas.config.loader import load_config
from atlas.runtime.application import AtlasApplication

from atlas.cli.config import config_group
from atlas.cli.doctor import doctor
from atlas.cli.models import models_group
from atlas.cli.network import network_group
from atlas.cli.plugins import plugins_group
from atlas.cli.runtime import runtime_group
from atlas.cli.system import logs, runtime_info, shell, update
from atlas.cli.voice import voice_group
from atlas.cli.ai import chat_command, provider_group, session_group

from rich.console import Console

console = Console()


@click.group()
@click.pass_context
def cli(ctx):
    """Atlas OS – AI Edge Operating System CLI.

    Atlas OS is a modular, offline-first AI Edge Operating System
    designed for Raspberry Pi 5 and edge devices.
    """
    # Initialize context
    if ctx.obj is None:
        ctx.obj = {}

    # Load configuration
    config_path = Path("configs/atlas.yaml")
    config = load_config(config_path)

    # Create application
    app = AtlasApplication(config)

    # Register core services in the container for CLI access
    app.container.register_instance("health_monitor", app.health_monitor)
    app.container.register_instance("heartbeat_service", app.heartbeat)
    app.container.register_instance("task_manager", app.tasks)
    app.container.register_instance("service_registry", app.registry)
    app.container.register_instance("lifecycle_manager", app._lifecycle)
    app.container.register_instance("config", app.config)

    # Store in context
    ctx.obj["app"] = app
    ctx.obj["container"] = app.container
    ctx.obj["config_path"] = config_path


# ============================================================
# Register all commands
# ============================================================
cli.add_command(config_group)
cli.add_command(logs)
cli.add_command(shell)
cli.add_command(runtime_info)
cli.add_command(update)
cli.add_command(models_group)
cli.add_command(network_group)
cli.add_command(voice_group)
cli.add_command(plugins_group)
cli.add_command(runtime_group)
cli.add_command(doctor)
# Phase 5: AI Engine
cli.add_command(chat_command)
cli.add_command(provider_group)
cli.add_command(session_group)


# ============================================================
# Core commands (moved from legacy)
# ============================================================
@cli.command()
@click.pass_context
def start(ctx):
    """Start the Atlas OS runtime."""
    app = ctx.obj["app"]
    console.print("[green]Starting Atlas OS...[/]")
    asyncio.run(app.run_forever())
    console.print("[green]✓ Atlas OS is running.[/]")


@cli.command()
def version():
    """Display Atlas OS version."""
    try:
        from atlas import __version__

        console.print(f"[bold]Atlas OS[/] version [cyan]{__version__}[/]")
    except ImportError:
        console.print("[bold]Atlas OS[/] version [yellow]unknown[/]")