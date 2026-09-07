"""Memory CLI commands for Atlas OS."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from atlas.memory.service import MemoryService, default_memory_persist_path

console = Console()


@click.group(name="memory")
def memory_group():
    """Persistent memory management commands."""
    pass


@memory_group.command(name="remember")
@click.argument("text")
@click.option("--category", default="fact", help="Memory category/tag", show_default=True)
@click.pass_context
def remember_cmd(ctx, text: str, category: str):
    """Store a new fact or preference in persistent memory."""
    app = ctx.obj.get("app") if ctx.obj else None
    data_dir = getattr(app.config, "data_dir", "./data") if app and hasattr(app, "config") else "./data"
    persist_path = str(default_memory_persist_path(data_dir))

    service = MemoryService(persist_path=persist_path)
    service.remember(text, metadata={"category": category})
    console.print(f"[green]✓ Remembered:[/] '{text}' [dim](category: {category})[/]")


@memory_group.command(name="recall")
@click.argument("query")
@click.option("--top-k", "-k", default=5, help="Number of memories to recall", show_default=True)
@click.pass_context
def recall_cmd(ctx, query: str, top_k: int):
    """Search and recall relevant memories matching a query."""
    app = ctx.obj.get("app") if ctx.obj else None
    data_dir = getattr(app.config, "data_dir", "./data") if app and hasattr(app, "config") else "./data"
    persist_path = str(default_memory_persist_path(data_dir))

    service = MemoryService(persist_path=persist_path)
    results = service.recall(query, top_k=top_k)

    if not results:
        console.print(f"[yellow]No memories found matching:[/] '{query}'")
        return

    console.print(f"[bold cyan]Recalled Memories for:[/] '{query}'\n")
    for idx, res in enumerate(results, 1):
        cat = res.metadata.get("category", "general")
        console.print(f"[bold green]#{idx}[/] [cyan]({res.score:.2f})[/] [dim][{cat}][/] {res.text}")


@memory_group.command(name="list")
@click.pass_context
def list_cmd(ctx):
    """List all stored persistent memories."""
    app = ctx.obj.get("app") if ctx.obj else None
    data_dir = getattr(app.config, "data_dir", "./data") if app and hasattr(app, "config") else "./data"
    persist_path = str(default_memory_persist_path(data_dir))

    service = MemoryService(persist_path=persist_path)
    entries = service.list_all() if hasattr(service, "list_all") else service._store._entries

    if not entries:
        console.print("[yellow]No memories stored yet.[/]")
        console.print("Add a memory with: [cyan]atlas memory remember \"...\"[/]")
        return

    table = Table(title=f"Stored Memories ({len(entries)} entries)")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Memory Text", style="bold")
    table.add_column("Category", style="cyan")

    for idx, entry in enumerate(entries, 1):
        cat = entry.metadata.get("category", "general") if hasattr(entry, "metadata") else "general"
        txt = entry.text if hasattr(entry, "text") else str(entry)
        table.add_row(str(idx), txt, cat)

    console.print(table)
