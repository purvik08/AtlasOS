"""Configuration management commands."""

import os
import subprocess
import tempfile
from pathlib import Path

import click
from rich.console import Console
from rich.syntax import Syntax

console = Console()


@click.group(name="config")
def config_group():
    """Manage Atlas OS configuration."""
    pass


@config_group.command(name="show")
@click.pass_context
def config_show(ctx):
    """Display current configuration (secrets redacted)."""
    container = ctx.obj["container"]
    config = container.resolve("config")
    if not config:
        console.print("[red]Configuration not loaded.[/]")
        return

    # Redact sensitive keys (e.g., api_keys, tokens)
    redacted = config.as_dict()
    for key in ["huggingface_token", "api_key", "jwt_secret"]:
        if key in redacted:
            redacted[key] = "******"

    syntax = Syntax(str(redacted), "yaml", theme="monokai", line_numbers=True)
    console.print(syntax)


@config_group.command(name="validate")
@click.pass_context
def config_validate(ctx):
    """Validate configuration schema and values."""
    container = ctx.obj["container"]
    config = container.resolve("config")
    if not config:
        console.print("[red]Configuration not loaded.[/]")
        return

    errors = config.validate()
    if errors:
        console.print("[red]Validation failed:[/]")
        for err in errors:
            console.print(f"  ✗ {err}")
    else:
        console.print("[green]✓ Configuration is valid.[/]")


@config_group.command(name="edit")
@click.pass_context
def config_edit(ctx):
    """Edit configuration file using $EDITOR."""
    config_path = ctx.obj.get("config_path")
    if not config_path:
        # Fallback to default location
        config_path = Path("configs/atlas.yaml")
    else:
        config_path = Path(config_path)

    # Read current content
    try:
        with open(config_path, encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        # If file doesn't exist, start with empty content
        content = ""

    # Create a temporary file
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".yaml",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp.write(content)
        temp_path = tmp.name

    try:
        # Open in editor
        subprocess.call([os.environ.get("EDITOR", "vim"), temp_path])
    except FileNotFoundError:
        console.print("[red]Editor not found. Set $EDITOR environment variable.[/]")
        return

    # Read edited content
    with open(temp_path, encoding="utf-8") as f:
        new_content = f.read()

    # Write back to config file
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    console.print(f"[green]✓ Configuration updated: {config_path}[/]")
