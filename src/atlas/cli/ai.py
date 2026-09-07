"""AI Engine CLI commands for Atlas OS.

Provides:
    atlas chat                     – Interactive chat REPL
    atlas provider list            – List registered providers
    atlas provider info <name>     – Detailed provider information
    atlas provider health <name>   – Provider health check
    atlas session list             – List active sessions
    atlas session new              – Create a new session
    atlas session delete <id>      – Delete a session

These commands integrate with :class:`~atlas.ai.manager.AIManager` via the
DI container registered in :mod:`atlas.cli.main`.
"""

from __future__ import annotations

import asyncio
import sys

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from atlas.ai.manager import AIManager, SessionNotFoundError
from atlas.ai.providers.base import ProviderStatus

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# atlas chat
# ---------------------------------------------------------------------------


@click.command(name="chat")
@click.option(
    "--provider", "-p", default=None, help="Provider name (llama_cpp, gemini, …)."
)
@click.option(
    "--role",
    "-r",
    default="auto",
    type=click.Choice(["local", "cloud", "auto"], case_sensitive=False),
    help="Provider role to use.",
    show_default=True,
)
@click.option("--model", "-m", default=None, help="Model ID to use for inference.")
@click.option(
    "--system",
    "-s",
    default="",
    help="System prompt for the session.",
)
@click.option(
    "--message",
    default=None,
    help="Single-shot message (non-interactive mode).",
)
@click.pass_context
def chat_command(ctx: click.Context, provider: str | None, role: str, model: str | None, system: str, message: str | None) -> None:
    """Start an AI chat session.

    By default opens an interactive REPL.  Pass --message for one-shot usage::

        atlas chat --message "Tell me about Raspberry Pi 5"
    """
    manager = _get_manager(ctx)

    try:
        session = manager.new_session(
            provider_name=provider,
            role=role,
            model_id=model,
            system_prompt=system,
        )
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Failed to create session: {exc}[/]")
        sys.exit(1)

    console.print(
        Panel(
            f"[bold cyan]Atlas Chat[/]\n"
            f"Session: [dim]{session.session_id}[/]\n"
            f"Provider: [green]{session.provider_name}[/]  "
            f"Model: [yellow]{session.model_id}[/]\n"
            f"Type [bold]/exit[/] or press [bold]Ctrl+C[/] to quit.",
            border_style="cyan",
        )
    )

    if message:
        # Non-interactive single-shot mode.
        _run_chat_turn(manager, session.session_id, message)
        return

    # Interactive REPL.
    while True:
        try:
            user_input = console.input("[bold cyan]You:[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/]")
            break

        if not user_input:
            continue
        if user_input.lower() in ("/exit", "/quit", "exit", "quit"):
            console.print("[dim]Goodbye.[/]")
            break

        _run_chat_turn(manager, session.session_id, user_input)


def _run_chat_turn(manager: AIManager, session_id: str, user_input: str) -> None:
    """Execute one chat turn and print the response."""
    try:
        response = asyncio.run(manager.chat(session_id, user_input))
        console.print(f"[bold green]Atlas:[/] {response.message.content}")
        if response.latency_ms >= 0:
            console.print(
                f"[dim]  ({response.provider_name} / {response.model_id} - "
                f"{response.latency_ms:.1f}ms)[/]"
            )
    except SessionNotFoundError as exc:
        console.print(f"[red]Session error: {exc}[/]")
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Error: {exc}[/]")


# ---------------------------------------------------------------------------
# atlas provider
# ---------------------------------------------------------------------------


@click.group(name="provider")
def provider_group() -> None:
    """Manage AI providers."""
    pass


@provider_group.command(name="list")
@click.pass_context
def provider_list(ctx: click.Context) -> None:
    """List all registered AI providers."""
    manager = _get_manager(ctx)
    providers = manager.list_providers()

    if not providers:
        console.print("[yellow]No providers registered.[/]")
        return

    table = Table(title="Registered AI Providers", box=box.ROUNDED)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Role", style="green")
    table.add_column("Available", style="yellow")
    table.add_column("Description", style="white")

    for p in providers:
        table.add_row(
            p.name,
            p.role.value,
            "yes" if p.available else "no",
            p.description,
        )
    console.print(table)


@provider_group.command(name="info")
@click.argument("provider_name")
@click.pass_context
def provider_info(ctx: click.Context, provider_name: str) -> None:
    """Show detailed information about a specific provider."""
    manager = _get_manager(ctx)

    try:
        provider = manager.router.get(provider_name)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]{exc}[/]")
        sys.exit(1)

    # Fetch models.
    try:
        models = asyncio.run(provider.list_models())
    except Exception:  # noqa: BLE001
        models = []

    content = (
        f"[bold]Provider:[/]     {provider.name}\n"
        f"[bold]Role:[/]         {provider.role.value}\n"
        f"[bold]Description:[/]  {provider.description}\n"
        f"[bold]Models:[/]       {len(models)}\n"
    )
    if models:
        model_lines = "\n".join(
            f"  - {m.model_id} ({'loaded' if m.loaded else 'unloaded'})"
            for m in models
        )
        content += f"\n{model_lines}"

    console.print(Panel(content, title=f"Provider: {provider.name}", border_style="cyan"))


@provider_group.command(name="health")
@click.argument("provider_name")
@click.pass_context
def provider_health(ctx: click.Context, provider_name: str) -> None:
    """Show health status for a provider."""
    manager = _get_manager(ctx)

    try:
        health = asyncio.run(manager.provider_health(provider_name))
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]{exc}[/]")
        sys.exit(1)

    status_color = {
        ProviderStatus.HEALTHY: "green",
        ProviderStatus.DEGRADED: "yellow",
        ProviderStatus.UNHEALTHY: "red",
        ProviderStatus.UNLOADED: "dim",
    }.get(health.status, "white")

    status_icon = {
        ProviderStatus.HEALTHY: "[+]",
        ProviderStatus.DEGRADED: "[!]",
        ProviderStatus.UNHEALTHY: "[x]",
        ProviderStatus.UNLOADED: "[-]",
    }.get(health.status, "[?]")

    content = (
        f"[bold]Provider:[/]      {health.provider_name}\n"
        f"[bold]Status:[/]        [{status_color}]{status_icon} {health.status.value}[/]\n"
        f"[bold]Loaded Models:[/] {', '.join(health.loaded_models) or 'none'}\n"
        f"[bold]Message:[/]       {health.message}\n"
        f"[bold]Checked At:[/]    {health.checked_at.strftime('%H:%M:%S UTC')}\n"
    )
    console.print(
        Panel(
            content,
            title=f"Health: {health.provider_name}",
            border_style=status_color,
        )
    )


# ---------------------------------------------------------------------------
# atlas session
# ---------------------------------------------------------------------------


@click.group(name="session")
def session_group() -> None:
    """Manage AI chat sessions."""
    pass


@session_group.command(name="list")
@click.pass_context
def session_list(ctx: click.Context) -> None:
    """List all active chat sessions."""
    manager = _get_manager(ctx)
    sessions = manager.list_sessions()

    if not sessions:
        console.print("[dim]No active sessions. Use 'atlas session new' to create one.[/]")
        return

    table = Table(title="Active Chat Sessions", box=box.ROUNDED)
    table.add_column("Session ID", style="cyan", no_wrap=True)
    table.add_column("Provider", style="green")
    table.add_column("Model", style="yellow")
    table.add_column("Messages", style="white")
    table.add_column("Created", style="dim")

    for s in sessions:
        table.add_row(
            s.session_id[:8] + "…",  # truncated for readability
            s.provider_name,
            s.model_id,
            str(len(s.history)),
            s.created_at.strftime("%H:%M:%S"),
        )
    console.print(table)


@session_group.command(name="new")
@click.option("--provider", "-p", default=None, help="Provider name.")
@click.option(
    "--role",
    "-r",
    default="auto",
    type=click.Choice(["local", "cloud", "auto"], case_sensitive=False),
    help="Provider role.",
    show_default=True,
)
@click.option("--model", "-m", default=None, help="Model ID.")
@click.option("--system", "-s", default="", help="System prompt.")
@click.pass_context
def session_new(ctx: click.Context, provider: str | None, role: str, model: str | None, system: str) -> None:
    """Create a new chat session and print its ID."""
    manager = _get_manager(ctx)
    try:
        session = manager.new_session(
            provider_name=provider,
            role=role,
            model_id=model,
            system_prompt=system,
        )
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Failed to create session: {exc}[/]")
        sys.exit(1)

    console.print(
        Panel(
            f"[bold]Session ID:[/]  [cyan]{session.session_id}[/]\n"
            f"[bold]Provider:[/]    [green]{session.provider_name}[/]\n"
            f"[bold]Model:[/]       [yellow]{session.model_id}[/]\n\n"
            f"[dim]Use 'atlas chat --message ...' with this session,[/]\n"
            f"[dim]or 'atlas session delete {session.session_id[:8]}...' to remove.[/]",
            title="Session Created",
            border_style="green",
        )
    )


@session_group.command(name="delete")
@click.argument("session_id")
@click.pass_context
def session_delete(ctx: click.Context, session_id: str) -> None:
    """Delete a chat session by ID."""
    manager = _get_manager(ctx)
    try:
        manager.delete_session(session_id)
        console.print(f"[green][+] Session '{session_id}' deleted.[/]")
    except SessionNotFoundError:
        console.print(f"[red]Session '{session_id}' not found.[/]")
        sys.exit(1)
