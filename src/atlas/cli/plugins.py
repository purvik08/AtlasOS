"""Plugin management commands for Atlas OS.

Provides plugin discovery, installation, enable/disable, and management.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from atlas.plugins.core import PluginManager

console = Console()


def _get_plugin_manager(ctx: click.Context) -> PluginManager:
    """Get or create PluginManager from context."""
    manager: PluginManager | None = ctx.obj.get("plugin_manager")
    if manager is None:
        app = ctx.obj["app"]
        plugins_dir = getattr(app.config, "plugins_dir", "./plugins")
        manager = PluginManager(plugins_dir)
        manager.discover()
        ctx.obj["plugin_manager"] = manager
    return manager


@click.group(name="plugins")
def plugins_group() -> None:
    """Manage Atlas OS plugins."""
    pass


@plugins_group.command(name="list")
@click.option("--enabled-only", is_flag=True, help="Show only enabled plugins")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def plugin_list(ctx: click.Context, enabled_only: bool, output_json: bool) -> None:
    """List all discovered plugins."""
    manager = _get_plugin_manager(ctx)

    if enabled_only:
        plugins = manager.list_enabled()
    else:
        plugins = manager.list_all()

    if not plugins:
        console.print("[yellow]No plugins found.[/]")
        msg = f"Place plugins in {manager.plugins_dir} or run 'atlas plugins install'."
        console.print(f"[dim]{msg}[/]")
        return

    if output_json:
        data = [
            {
                "name": p.manifest.name,
                "version": p.manifest.version,
                "description": p.manifest.description,
                "author": p.manifest.author,
                "enabled": p.enabled,
                "loaded": p.loaded,
                "path": str(p.path),
                "error": p.error,
            }
            for p in plugins
        ]
        console.print(json.dumps(data, indent=2))
        return

    table = Table(title="Plugins", box=None)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Version", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Description", style="white")
    table.add_column("Author", style="dim")
    table.add_column("Path", style="dim")

    for p in plugins:
        if p.loaded:
            status = "[green]loaded[/]"
        elif p.enabled:
            status = "[blue]enabled[/]"
        else:
            status = "[dim]disabled[/]"
        if p.error:
            status = "[red]error[/]"

        table.add_row(
            p.manifest.name,
            p.manifest.version,
            status,
            p.manifest.description or "—",
            p.manifest.author or "—",
            str(p.path),
        )

    console.print(table)


@plugins_group.command(name="info")
@click.argument("name")
@click.pass_context
def plugin_info(ctx: click.Context, name: str) -> None:
    """Show detailed information about a plugin."""
    manager = _get_plugin_manager(ctx)
    plugin = manager.get(name)

    if not plugin:
        console.print(f"[red]Plugin '{name}' not found.[/]")
        sys.exit(1)

    manifest = plugin.manifest

    content = (
        f"[bold]Name:[/]        {manifest.name}\n"
        f"[bold]Version:[/]     {manifest.version}\n"
        f"[bold]Description:[/] {manifest.description or '—'}\n"
        f"[bold]Author:[/]      {manifest.author or '—'}\n"
        f"[bold]License:[/]     {manifest.license}\n"
        f"[bold]Homepage:[/]    {manifest.homepage or '—'}\n"
        f"[bold]Repository:[/]  {manifest.repository or '—'}\n"
        f"[bold]Entry Point:[/] {manifest.entry_point}\n"
        f"[bold]Atlas Version:[/] {manifest.atlas_version}\n"
    )

    if plugin.loaded:
        status = "[green]loaded[/]"
    elif plugin.enabled:
        status = "[blue]enabled[/]"
    else:
        status = "[dim]disabled[/]"

    content += f"[bold]Status:[/]      {status}\n"

    if plugin.error:
        content += f" [red](error: {plugin.error})[/]\n"

    content += f"[bold]Path:[/]        {plugin.path}\n"

    if manifest.dependencies:
        content += f"[bold]Dependencies:[/] {', '.join(manifest.dependencies)}\n"
    if manifest.permissions:
        content += f"[bold]Permissions:[/] {', '.join(manifest.permissions)}\n"

    console.print(Panel(content, title=f"Plugin: {name}", border_style="cyan"))


@plugins_group.command(name="enable")
@click.argument("name")
@click.pass_context
def plugin_enable(ctx: click.Context, name: str) -> None:
    """Enable a plugin."""
    manager = _get_plugin_manager(ctx)
    if manager.enable(name):
        console.print(f"[green][+] Plugin '{name}' enabled.[/]")
    else:
        console.print(f"[red]Plugin '{name}' not found.[/]")
        sys.exit(1)


@plugins_group.command(name="disable")
@click.argument("name")
@click.pass_context
def plugin_disable(ctx: click.Context, name: str) -> None:
    """Disable a plugin."""
    manager = _get_plugin_manager(ctx)
    if manager.disable(name):
        console.print(f"[green][+] Plugin '{name}' disabled.[/]")
    else:
        console.print(f"[red]Plugin '{name}' not found.[/]")
        sys.exit(1)


@plugins_group.command(name="install")
@click.argument("source")
@click.option("--name", default=None, help="Override plugin name")
@click.pass_context
def plugin_install(ctx: click.Context, source: str, name: str | None) -> None:
    """Install a plugin from a zip file or directory."""
    manager = _get_plugin_manager(ctx)
    source_path = Path(source)

    try:
        if source_path.is_dir():
            # Install from directory
            manifest_path = source_path / "atlas-plugin.yaml"
            if not manifest_path.exists():
                console.print("[red]No atlas-plugin.yaml found in directory.[/]")
                sys.exit(1)

            # Copy to plugins dir
            from atlas.plugins.core import PluginManifest
            manifest = PluginManifest.from_yaml(manifest_path)
            target_name = name or manifest.name
            target_dir = manager.plugins_dir / target_name

            if target_dir.exists():
                console.print(f"[red]Plugin '{target_name}' already exists.[/]")
                sys.exit(1)

            import shutil
            shutil.copytree(source_path, target_dir)
            manager.discover()
            console.print(f"[green][+] Plugin '{target_name}' installed from directory.[/]")

        elif source_path.suffix == ".zip":
            # Install from zip
            plugin_info = manager.install_from_zip(source_path)
            console.print(f"[green][+] Plugin '{plugin_info.manifest.name}' installed from zip.[/]")

        else:
            console.print("[red]Source must be a directory or .zip file.[/]")
            sys.exit(1)

    except Exception as exc:
        console.print(f"[red]Installation failed: {exc}[/]")
        sys.exit(1)


@plugins_group.command(name="uninstall")
@click.argument("name")
@click.confirmation_option(prompt="Are you sure you want to uninstall this plugin?")
@click.pass_context
def plugin_uninstall(ctx: click.Context, name: str) -> None:
    """Uninstall a plugin (removes files)."""
    manager = _get_plugin_manager(ctx)
    if manager.uninstall(name):
        console.print(f"[green][+] Plugin '{name}' uninstalled.[/]")
    else:
        console.print(f"[red]Plugin '{name}' not found.[/]")
        sys.exit(1)


@plugins_group.command(name="create")
@click.argument("name")
@click.option("--path", default=None, help="Custom path for plugin")
@click.pass_context
def plugin_create(ctx: click.Context, name: str, path: str | None) -> None:
    """Create a new plugin template."""
    manager = _get_plugin_manager(ctx)

    try:
        plugin_path = manager.create_plugin_template(name, path)
        console.print(f"[green][+] Plugin template created at: {plugin_path}[/]")
        console.print("[dim]Edit atlas-plugin.yaml and main.py to implement your plugin.[/]")
    except Exception as exc:
        console.print(f"[red]Failed to create plugin: {exc}[/]")
        sys.exit(1)


@plugins_group.command(name="load")
@click.argument("name")
@click.pass_context
def plugin_load(ctx: click.Context, name: str) -> None:
    """Load a plugin into the running application."""
    manager = _get_plugin_manager(ctx)
    plugin = manager.get(name)

    if not plugin:
        console.print(f"[red]Plugin '{name}' not found.[/]")
        sys.exit(1)

    if not plugin.enabled:
        msg = f"Plugin '{name}' is not enabled. Run 'atlas plugins enable {name}' first."
        console.print(f"[red]{msg}[/]")
        sys.exit(1)

    app = ctx.obj.get("app")
    if not app:
        console.print("[red]Application context not available.[/]")
        sys.exit(1)

    console.print(f"[cyan]Loading plugin '{name}'...[/]")
    try:
        import asyncio
        asyncio.run(manager.load_plugin(name, app))
        console.print(f"[green][+] Plugin '{name}' loaded successfully.[/]")
    except Exception as exc:
        console.print(f"[red]Failed to load plugin: {exc}[/]")
        sys.exit(1)


@plugins_group.command(name="unload")
@click.argument("name")
@click.pass_context
def plugin_unload(ctx: click.Context, name: str) -> None:
    """Unload a plugin from the running application."""
    manager = _get_plugin_manager(ctx)

    import asyncio
    asyncio.run(manager.unload_plugin(name))
    console.print(f"[green][+] Plugin '{name}' unloaded.[/]")
