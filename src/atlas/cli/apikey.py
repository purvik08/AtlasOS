"""API Key management CLI commands for Atlas OS."""

from __future__ import annotations

import click
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from atlas.secrets import (
    delete_api_key,
    get_api_key,
    list_api_keys,
    set_api_key,
)

console = Console()


@click.group(name="apikey")
def apikey_group() -> None:
    """Manage API keys for cloud providers."""
    pass


@apikey_group.command(name="list")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def apikey_list(output_json: bool) -> None:
    """List all stored API keys."""
    providers = list_api_keys()

    if not providers:
        console.print("[yellow]No API keys stored.[/]")
        console.print("[dim]Run 'atlas apikey set <provider>' to add one.[/]")
        return

    if output_json:
        import json
        console.print(json.dumps(providers, indent=2))
        return

    table = Table(title="Stored API Keys", box=None)
    table.add_column("Provider", style="cyan")
    table.add_column("Status", style="green")

    for provider in providers:
        key = get_api_key(provider)
        masked = key[:8] + "..." + key[-4:] if key and len(key) > 12 else "***"
        table.add_row(provider, f"[green]set[/] ({masked})")

    console.print(table)


@apikey_group.command(name="set")
@click.argument("provider", type=click.Choice(["gemini", "deepseek", "kimi", "qwen"]))
@click.option("--key", "-k", default=None, help="API key value (will prompt if omitted)")
@click.option(
    "--env", is_flag=True, help="Read from environment variable ATLAS_AI_<PROVIDER>_API_KEY"
)
def apikey_set(provider: str, key: str | None, env: bool) -> None:
    """Set an API key for a cloud provider."""
    if env:
        import os
        env_var = f"ATLAS_AI__{provider.upper()}_API_KEY"
        key = os.environ.get(env_var)
        if not key:
            console.print(f"[red]Environment variable {env_var} not set.[/]")
            return

    if not key:
        console.print(f"[cyan]Enter API key for {provider}:[/]")
        key = Prompt.ask("", password=True)

    if not key:
        console.print("[red]No API key provided.[/]")
        return

    if set_api_key(provider, key):
        console.print(f"[green][+] API key for {provider} stored securely.[/]")
    else:
        console.print(f"[red]Failed to store API key for {provider}.[/]")


@apikey_group.command(name="get")
@click.argument("provider", type=click.Choice(["gemini", "deepseek", "kimi", "qwen"]))
@click.option("--show", is_flag=True, help="Show full key (default: masked)")
def apikey_get(provider: str, show: bool) -> None:
    """Get an API key for a cloud provider."""
    key = get_api_key(provider)
    if not key:
        console.print(f"[yellow]No API key stored for {provider}.[/]")
        return

    if show:
        console.print(key)
    else:
        masked = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
        console.print(f"{provider}: {masked}")


@apikey_group.command(name="delete")
@click.argument("provider", type=click.Choice(["gemini", "deepseek", "kimi", "qwen"]))
@click.confirmation_option(prompt="Are you sure you want to delete this API key?")
def apikey_delete(provider: str) -> None:
    """Delete an API key for a cloud provider."""
    if delete_api_key(provider):
        console.print(f"[green][+] API key for {provider} deleted.[/]")
    else:
        console.print(f"[yellow]No API key found for {provider}.[/]")


@apikey_group.command(name="sync")
@click.option("--to-config", is_flag=True, help="Sync stored keys to current config")
@click.option("--from-config", is_flag=True, help="Sync config keys to secure storage")
@click.pass_context
def apikey_sync(ctx: click.Context, to_config: bool, from_config: bool) -> None:
    """Sync API keys between secure storage and configuration."""
    from atlas.config.loader import load_config

    config_path = ctx.obj.get("config_path", "configs/atlas.yaml")
    config = load_config(config_path)

    if to_config:
        from atlas.secrets import sync_secrets_to_config
        sync_secrets_to_config(config)
        console.print("[green][+] Synced stored API keys to configuration.[/]")

    if from_config:
        from atlas.secrets import sync_config_to_secrets
        sync_config_to_secrets(config)
        console.print("[green][+] Synced configuration API keys to secure storage.[/]")

    if not to_config and not from_config:
        console.print("[yellow]Specify --to-config or --from-config.[/]")