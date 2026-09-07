"""Configuration management commands."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import click
import yaml
from rich.console import Console
from rich.syntax import Syntax

from atlas.config.loader import load_config

console = Console()


@click.group(name="config")
def config_group() -> None:
    """Manage Atlas OS configuration."""
    pass


@config_group.command(name="show")
@click.pass_context
def config_show(ctx: click.Context) -> None:
    """Display current configuration (secrets redacted)."""
    container = ctx.obj["container"]
    config = container.resolve("config")
    if not config:
        console.print("[red]Configuration not loaded.[/]")
        return

    # Redact sensitive keys (e.g., api_keys, tokens)
    redacted = config.model_dump()
    for key in ["huggingface_token", "api_key", "jwt_secret"]:
        if key in redacted:
            redacted[key] = "******"

    syntax = Syntax(str(redacted), "yaml", theme="monokai", line_numbers=True)
    console.print(syntax)


@config_group.command(name="validate")
@click.pass_context
def config_validate(ctx: click.Context) -> None:
    """Validate configuration schema and values."""
    container = ctx.obj["container"]
    config = container.resolve("config")
    if not config:
        console.print("[red]Configuration not loaded.[/]")
        return

    # Pydantic validates on construction; just confirm it's valid
    console.print("[green][+] Configuration is valid.[/]")


@config_group.command(name="edit")
@click.option("--validate/--no-validate", default=True, help="Validate YAML syntax before saving")
@click.pass_context
def config_edit(ctx: click.Context, validate: bool) -> None:
    """Edit configuration file using $EDITOR with validation."""
    config_path = ctx.obj.get("config_path")
    if not config_path:
        # Fallback to default location
        config_path = Path("configs/atlas.yaml")
    else:
        config_path = Path(config_path)

    # Read current content
    try:
        with config_path.open(encoding="utf-8") as f:
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
        editor = os.environ.get("EDITOR", "vim")
        subprocess.call([editor, temp_path])
    except FileNotFoundError:
        console.print("[red]Editor not found. Set $EDITOR environment variable.[/]")
        return

    # Read edited content
    with open(temp_path, encoding="utf-8") as f:
        new_content = f.read()

    if new_content == content:
        console.print("[dim]No changes made.[/]")
        return

    # Validate YAML syntax
    if validate:
        try:
            parsed = yaml.safe_load(new_content)
            if parsed is not None and not isinstance(parsed, dict):
                console.print("[red]Config must be a YAML mapping (dictionary) at top level.[/]")
                return
        except yaml.YAMLError as exc:
            console.print(f"[red]YAML syntax error: {exc}[/]")
            return

        # Validate against Pydantic schema
        try:
            # Write to a temp file and load with load_config to test
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".yaml",
                delete=False,
                encoding="utf-8",
            ) as test_file:
                test_file.write(new_content)
                test_path = test_file.name

            load_config(test_path)
            # If we get here, it's valid
            os.unlink(test_path)
            console.print("[green][+] Configuration syntax and schema validation passed.[/]")
        except Exception as exc:
            console.print(f"[red]Configuration validation failed: {exc}[/]")
            return

    # Write back to config file
    with config_path.open("w", encoding="utf-8") as f:
        f.write(new_content)

    console.print(f"[green][+] Configuration updated: {config_path}[/]")


@config_group.command(name="get")
@click.argument("key")
@click.pass_context
def config_get(ctx: click.Context, key: str) -> None:
    """Get a specific configuration value by dot-notation key (e.g., ai.default_provider)."""
    container = ctx.obj["container"]
    config = container.resolve("config")
    if not config:
        console.print("[red]Configuration not loaded.[/]")
        return

    # Navigate nested config using dot notation
    value: Any = config
    try:
        for part in key.split("."):
            if hasattr(value, part):
                value = getattr(value, part)
            elif isinstance(value, dict):
                value = value[part]
            else:
                raise KeyError(part)
    except (KeyError, AttributeError):
        console.print(f"[red]Key '{key}' not found.[/]")
        return

    console.print(f"{key} = {value}")


@config_group.command(name="set")
@click.argument("key")
@click.argument("value")
@click.option(
    "--persist", is_flag=True, help="Write to config file (default: current session only)"
)
@click.pass_context
def config_set(ctx: click.Context, key: str, value: str, persist: bool) -> None:
    """Set a configuration value by dot-notation key.

    Example: atlas config set ai.default_provider llama_cpp
    """
    container = ctx.obj["container"]
    config = container.resolve("config")
    if not config:
        console.print("[red]Configuration not loaded.[/]")
        return

    # Parse value (try JSON first, then string)
    import json
    try:
        parsed_value = json.loads(value)
    except json.JSONDecodeError:
        parsed_value = value

    # Navigate to parent and set
    parts = key.split(".")
    parent = config
    for part in parts[:-1]:
        if hasattr(parent, part):
            parent = getattr(parent, part)
        elif isinstance(parent, dict):
            parent = parent[part]
        else:
            console.print(f"[red]Cannot navigate to '{part}' in config.[/]")
            return

    final_key = parts[-1]
    try:
        if hasattr(parent, final_key):
            setattr(parent, final_key, parsed_value)
        elif isinstance(parent, dict):
            parent[final_key] = parsed_value
        else:
            console.print(f"[red]Cannot set '{final_key}' on config object.[/]")
            return
    except Exception as exc:
        console.print(f"[red]Failed to set value: {exc}[/]")
        return

    console.print(f"[green][+] Set {key} = {parsed_value} (session only)[/]")

    if persist:
        _ = ctx.obj.get("config_path", Path("configs/atlas.yaml"))
        # Note: Full persistence requires rewriting the YAML file
        console.print("[yellow]Persistence not yet implemented. Edit the YAML file directly.[/]")


@config_group.command(name="reset")
@click.confirmation_option(prompt="Reset all configuration to defaults?")
@click.pass_context
def config_reset(ctx: click.Context) -> None:
    """Reset configuration to defaults."""
    config_path = ctx.obj.get("config_path", Path("configs/atlas.yaml"))
    if config_path.exists():
        config_path.unlink()
    console.print("[green][+] Configuration reset to defaults.[/]")
    console.print("[dim]Restart Atlas OS to apply.[/]")
