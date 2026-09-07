"""Model management CLI commands for Atlas OS.

Replaces the Phase 3 stub with real model registry integration.
All commands delegate to :class:`~atlas.ai.manager.AIManager`.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from atlas.ai.manager import AIManager
from atlas.ai.model import ModelNotFoundError

console = Console()


def _get_manager(ctx: click.Context) -> AIManager:
    """Resolve AIManager and ensure it is started.

    Every `atlas` invocation is a new process, so the manager is always
    unstarted.  start() scans models_dir and registers providers — without
    it, ModelRegistry is empty and no inference works.
    """
    manager: AIManager | None = ctx.obj.get("ai_manager")
    if manager is None:
        app = ctx.obj["app"]
        try:
            manager = app.container.resolve("ai_manager")
        except Exception:
            manager = AIManager(app.config)
        asyncio.run(manager.start())  # always required — populates ModelRegistry
        ctx.obj["ai_manager"] = manager
    return manager


@click.group(name="models")
def models_group() -> None:
    """Manage AI models."""
    pass


@models_group.command(name="list")
@click.option("--loaded-only", is_flag=True, help="Show only loaded models.")
@click.pass_context
def model_list(ctx: click.Context, loaded_only: bool) -> None:
    """List all discovered models and their status."""
    manager = _get_manager(ctx)
    all_models = manager.list_models()
    if loaded_only:
        models = [
            m
            for m in all_models
            if m.provider_name == "llama_cpp" and m.loaded
        ]
    else:
        models = all_models

    if not models:
        if loaded_only:
            console.print("[dim]No models currently loaded.[/]")
        else:
            console.print(
                "[yellow]No models found.[/] "
                "Place .gguf files in your models_dir or run 'atlas models download'."
            )
        return

    table = Table(
        title="AI Models" + (" (loaded only)" if loaded_only else ""),
        box=box.ROUNDED,
    )
    table.add_column("Model ID", style="cyan", no_wrap=True)
    table.add_column("Display Name", style="white")
    table.add_column("Provider", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Size", style="dim")

    for m in models:
        size_str = (
            f"{m.size_bytes / (1024 ** 3):.2f} GB"
            if m.size_bytes > 1024 ** 3
            else f"{m.size_bytes / (1024 ** 2):.1f} MB"
            if m.size_bytes > 0
            else "unknown"
        )
        if m.provider_name == "llama_cpp":
            status = "[green]loaded[/]" if m.loaded else "[dim]unloaded[/]"
        else:
            try:
                p = manager.router.get(m.provider_name)
                ph = asyncio.run(p.health())
                from atlas.ai.providers.base import ProviderStatus
                is_healthy = ph.status == ProviderStatus.HEALTHY
                status = "[green]available[/]" if is_healthy else "[yellow]unauthenticated[/]"
            except Exception:
                status = "[yellow]unauthenticated[/]"

        table.add_row(m.model_id, m.display_name, m.provider_name, status, size_str)

    console.print(table)


@models_group.command(name="load")
@click.argument("model_id")
@click.option("--provider", "-p", default=None, help="Provider to use (optional).")
@click.pass_context
def model_load(ctx: click.Context, model_id: str, provider: str | None) -> None:
    """Load a model into memory."""
    manager = _get_manager(ctx)
    console.print(f"[cyan]Loading model:[/] {model_id} …")
    try:
        asyncio.run(manager.load_model(model_id, provider_name=provider))
        console.print(f"[green][+] Model '{model_id}' loaded successfully.[/]")
    except (ModelNotFoundError, ValueError) as exc:
        console.print(f"[red]Model not found:[/] {exc}")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Failed to load model:[/] {exc}")
        sys.exit(1)


@models_group.command(name="unload")
@click.argument("model_id")
@click.option("--provider", "-p", default=None, help="Provider to use (optional).")
@click.pass_context
def model_unload(ctx: click.Context, model_id: str, provider: str | None) -> None:
    """Unload a model from memory."""
    manager = _get_manager(ctx)
    console.print(f"[cyan]Unloading model:[/] {model_id} …")
    try:
        asyncio.run(manager.unload_model(model_id, provider_name=provider))
        console.print(f"[green][+] Model '{model_id}' unloaded.[/]")
    except ModelNotFoundError as exc:
        console.print(f"[red]Model not found:[/] {exc}")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Failed to unload model:[/] {exc}")
        sys.exit(1)


@models_group.command(name="info")
@click.argument("model_id")
@click.pass_context
def model_info(ctx: click.Context, model_id: str) -> None:
    """Show detailed information about a specific model."""
    manager = _get_manager(ctx)
    try:
        info = manager.model_registry.get(model_id)
    except ModelNotFoundError as exc:
        console.print(f"[red]{exc}[/]")
        sys.exit(1)

    size_str = (
        f"{info.size_bytes / (1024 ** 3):.2f} GB"
        if info.size_bytes > 1024 ** 3
        else f"{info.size_bytes / (1024 ** 2):.1f} MB"
        if info.size_bytes > 0
        else "unknown"
    )

    if info.provider_name == "llama_cpp":
        status_str = "[green]loaded[/]" if info.loaded else "[dim]unloaded[/]"
    else:
        try:
            p = manager.router.get(info.provider_name)
            ph = asyncio.run(p.health())
            from atlas.ai.providers.base import ProviderStatus
            is_healthy = ph.status == ProviderStatus.HEALTHY
            status_str = "[green]available[/]" if is_healthy else "[yellow]unauthenticated[/]"
        except Exception:
            status_str = "[yellow]unauthenticated[/]"

    content = (
        f"[bold]Model ID:[/]      {info.model_id}\n"
        f"[bold]Display Name:[/] {info.display_name}\n"
        f"[bold]Provider:[/]     {info.provider_name}\n"
        f"[bold]Status:[/]       {status_str}\n"
        f"[bold]Size:[/]         {size_str}\n"
        f"[bold]Description:[/]  {info.description or 'n/a'}\n"
    )
    console.print(Panel(content, title=f"Model: {info.model_id}", border_style="cyan"))


@models_group.command(name="download")
@click.argument("model_id")
@click.option(
    "--url",
    "-u",
    default=None,
    help="Direct download URL (alternative to --repo).",
)
@click.option(
    "--repo",
    default=None,
    help="Hugging Face repo ID, e.g. TheBloke/Llama-2-7B-GGUF.",
)
@click.option(
    "--filename",
    default=None,
    help="Filename within the HF repo (required with --repo).",
)
@click.option("--token", default=None, help="Hugging Face token for gated models.")
@click.option("--overwrite", is_flag=True, help="Re-download even if file exists.")
@click.pass_context
def model_download(
    ctx: click.Context,
    model_id: str,
    url: str | None,
    repo: str | None,
    filename: str | None,
    token: str | None,
    overwrite: bool,
) -> None:
    """Download a model from Hugging Face or a direct URL.

    Examples::

        atlas models download my-model --url https://example.com/model.gguf

        atlas models download llama2-7b \\
            --repo TheBloke/Llama-2-7B-GGUF \\
            --filename llama-2-7b.Q4_K_M.gguf \\
            --token hf_...
    """
    manager = _get_manager(ctx)

    if not url and not repo:
        console.print("[red]Provide --url or --repo.[/]")
        sys.exit(1)

    if repo and not filename:
        console.print("[red]--filename is required when using --repo.[/]")
        sys.exit(1)

    console.print(f"[cyan]Downloading model:[/] {model_id} …")

    async def _run() -> Any:
        if repo:
            assert filename is not None  # Validated above
            return await manager.downloader.download_from_huggingface(
                repo_id=repo,
                filename=filename,
                token=token,
                overwrite=overwrite,
            )
        assert url is not None  # Validated above
        return await manager.download_model(
            model_id=model_id,
            source_url=url,
            overwrite=overwrite,
        )

    try:
        result = asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Download failed:[/] {exc}")
        sys.exit(1)

    if result.success:
        console.print(
            f"[green][+] Downloaded '{model_id}' to {result.path} "
            f"({result.bytes_downloaded / 1024:.0f} KB).[/]"
        )
    else:
        console.print(f"[red]Download failed:[/] {result.error}")
        sys.exit(1)


@models_group.command(name="remove")
@click.argument("model_id")
@click.confirmation_option(prompt="Are you sure you want to remove this model?")
@click.pass_context
def model_remove(ctx: click.Context, model_id: str) -> None:
    """Remove a model from the registry (does not delete the file)."""
    manager = _get_manager(ctx)
    try:
        manager.model_registry.unregister(model_id)
        console.print(f"[green][+] Model '{model_id}' removed from registry.[/]")
        console.print("[dim]The file is still on disk. Delete it manually if desired.[/]")
    except ModelNotFoundError as exc:
        console.print(f"[red]{exc}[/]")
        sys.exit(1)
