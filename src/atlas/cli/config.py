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

    # AtlasConfig is a Pydantic BaseSettings model; .model_dump() returns a
    # plain dict of all fields including nested ones (e.g. ai: {...}).
    raw: dict = config.model_dump()

    # Redact known secret fields so they are never printed in full.
    _SECRET_FIELDS = {"gemini_api_key", "deepseek_api_key", "kimi_api_key", "qwen_api_key"}

    def _redact(d: dict) -> dict:
        out = {}
        for k, v in d.items():
            if k in _SECRET_FIELDS:
                out[k] = "******" if v else ""
            elif isinstance(v, dict):
                out[k] = _redact(v)
            else:
                out[k] = v
        return out

    redacted = _redact(raw)

    import yaml  # pyyaml is already in dependencies

    yaml_str = yaml.dump(redacted, default_flow_style=False, sort_keys=True)
    syntax = Syntax(yaml_str, "yaml", theme="monokai", line_numbers=True)
    console.print(syntax)


@config_group.command(name="validate")
@click.pass_context
def config_validate(ctx):
    """Validate configuration schema and values.

    AtlasConfig uses Pydantic for validation; if the config was loaded
    successfully it is structurally valid. This command re-confirms that
    and reports it clearly.
    """
    container = ctx.obj["container"]
    config = container.resolve("config")
    if not config:
        console.print("[red]Configuration not loaded.[/]")
        return

    # Pydantic validates on construction; reaching here means no schema
    # errors occurred.  We surface any additional semantic checks below.
    issues: list[str] = []

    if not Path(config.models_dir).exists():
        issues.append(f"models_dir '{config.models_dir}' does not exist on disk.")

    if not Path(config.data_dir).exists():
        issues.append(f"data_dir '{config.data_dir}' does not exist on disk.")

    if config.ai.default_role not in ("local", "cloud", "auto"):
        issues.append(
            f"ai.default_role '{config.ai.default_role}' is not one of: local, cloud, auto."
        )

    if issues:
        console.print("[red]Validation warnings:[/]")
        for issue in issues:
            console.print(f"  [red]✗[/] {issue}")
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
