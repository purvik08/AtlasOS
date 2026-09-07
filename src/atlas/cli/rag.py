"""RAG knowledge base CLI commands for Atlas OS."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from atlas.memory.embedder import create_best_embedder
from atlas.memory.service import MemoryService, default_memory_persist_path
from atlas.rag.service import RAGService

console = Console()


def _rag_service(data_dir: str | Path) -> RAGService:
    embedder = create_best_embedder()
    memory = MemoryService(
        embedder=embedder,
        persist_path=default_memory_persist_path(data_dir),
    )
    return RAGService(embedder=embedder, data_dir=data_dir, memory_service=memory)


@click.group(name="rag")
def rag_group():
    """RAG (Retrieval-Augmented Generation) knowledge base commands."""
    pass


@rag_group.command(name="ingest")
@click.argument("target", type=click.Path(exists=True))
@click.option("--title", default=None, help="Custom document title")
@click.option("--recursive", "-r", is_flag=True, help="Recursively ingest all documents in a directory")
@click.pass_context
def ingest_cmd(ctx, target: str, title: str | None, recursive: bool):
    """Ingest a file or directory into the RAG knowledge base."""
    target_path = Path(target)
    app = ctx.obj.get("app") if ctx.obj else None
    data_dir = getattr(app.config, "data_dir", "./data") if app and hasattr(app, "config") else "./data"

    service = _rag_service(data_dir)

    if target_path.is_dir():
        console.print(f"[cyan]Ingesting directory:[/] {target_path}")
        results = service.ingest_directory(target_path, recursive=recursive)
        success_count = sum(1 for r in results if r.success)
        total_chunks = sum(r.chunk_count for r in results if r.success)
        console.print(
            f"[green]✓ Ingested {success_count}/{len(results)} files ({total_chunks} total chunks indexed).[/]"
        )
    else:
        res = service.ingest_file(target_path, title=title)
        if res.success:
            console.print(
                f"[green]✓ Successfully ingested '{res.title}' into RAG ({res.chunk_count} chunks indexed).[/]"
            )
            console.print(f"  [dim]Doc ID:[/] [cyan]{res.doc_id}[/]")
        else:
            console.print(f"[red]✗ Ingestion failed:[/] {res.error}")


@rag_group.command(name="search")
@click.argument("query")
@click.option("--top-k", "-k", default=3, help="Number of chunks to retrieve", show_default=True)
@click.option("--threshold", "-t", default=0.0, help="Minimum similarity threshold", show_default=True)
@click.pass_context
def search_cmd(ctx, query: str, top_k: int, threshold: float):
    """Search knowledge base chunks by semantic similarity."""
    app = ctx.obj.get("app") if ctx.obj else None
    data_dir = getattr(app.config, "data_dir", "./data") if app and hasattr(app, "config") else "./data"

    service = _rag_service(data_dir)
    results = service.search(query, top_k=top_k, threshold=threshold)

    if not results:
        console.print(f"[yellow]No matching knowledge chunks found for:[/] '{query}'")
        return

    console.print(f"[bold cyan]Knowledge Base Search Results for:[/] '{query}'\n")
    for idx, r in enumerate(results, 1):
        console.print(
            f"[bold green]#{idx} [{r.doc_title}][/] (Score: [cyan]{r.score:.3f}[/] | Chunk {r.chunk_index + 1}/{r.total_chunks})"
        )
        if r.source_path:
            console.print(f"  [dim]Source:[/] {r.source_path}")
        console.print(f"  [italic]{r.text.strip()}[/]\n")


@rag_group.command(name="list")
@click.pass_context
def list_cmd(ctx):
    """List all indexed documents in the RAG knowledge base."""
    app = ctx.obj.get("app") if ctx.obj else None
    data_dir = getattr(app.config, "data_dir", "./data") if app and hasattr(app, "config") else "./data"

    service = _rag_service(data_dir)
    docs = service.list_documents()

    if not docs:
        console.print("[yellow]No documents indexed in RAG knowledge base.[/]")
        console.print("Ingest a document with: [cyan]atlas rag ingest <path>[/]")
        return

    table = Table(title=f"RAG Knowledge Base ({len(docs)} documents)")
    table.add_column("Doc ID", style="cyan")
    table.add_column("Title", style="bold")
    table.add_column("Chunks", justify="right")
    table.add_column("Size", justify="right")
    table.add_column("Source", style="dim")

    for d in docs:
        size_str = f"{d.file_size_bytes / 1024:.1f} KB" if d.file_size_bytes > 0 else "N/A"
        table.add_row(
            d.doc_id,
            d.title,
            str(d.chunk_count),
            size_str,
            Path(d.source_path).name if d.source_path else "inline",
        )

    console.print(table)


@rag_group.command(name="delete")
@click.argument("doc_id")
@click.pass_context
def delete_cmd(ctx, doc_id: str):
    """Delete a document from the RAG knowledge base."""
    app = ctx.obj.get("app") if ctx.obj else None
    data_dir = getattr(app.config, "data_dir", "./data") if app and hasattr(app, "config") else "./data"

    service = _rag_service(data_dir)
    ok = service.delete_document(doc_id)
    if ok:
        console.print(f"[green]✓ Deleted document '{doc_id}' and all associated chunk embeddings.[/]")
    else:
        console.print(f"[red]✗ Document '{doc_id}' not found.[/]")


@rag_group.command(name="clear")
@click.confirmation_option(prompt="Are you sure you want to clear the entire RAG knowledge base?")
@click.pass_context
def clear_cmd(ctx):
    """Clear all indexed documents and embeddings."""
    app = ctx.obj.get("app") if ctx.obj else None
    data_dir = getattr(app.config, "data_dir", "./data") if app and hasattr(app, "config") else "./data"

    service = _rag_service(data_dir)
    service.clear()
    console.print("[green]✓ RAG knowledge base cleared.[/]")
