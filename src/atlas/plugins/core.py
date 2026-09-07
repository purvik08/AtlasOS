"""Plugin system core for Atlas OS.

Provides plugin discovery, manifest parsing, sandboxed loading, and lifecycle management.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import logging
import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from atlas.utils import get_python_executable
from atlas.plugins.permissions import (
    Permission,
    PermissionDeniedError,
    PermissionRegistry,
    check_permission,
    get_permission_registry,
)

logger = logging.getLogger(__name__)


@dataclass
class PluginManifest:
    """Plugin manifest (atlas-plugin.yaml)"""
    name: str
    version: str
    description: str = ""
    author: str = ""
    license: str = "MIT"
    homepage: str = ""
    repository: str = ""
    entry_point: str = "main:Plugin"
    dependencies: list[str] = field(default_factory=list)
    atlas_version: str = ">=0.1.0"
    permissions: list[str] = field(default_factory=list)
    config_schema: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: Path) -> PluginManifest:
        """Load manifest from YAML file."""
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "license": self.license,
            "homepage": self.homepage,
            "repository": self.repository,
            "entry_point": self.entry_point,
            "dependencies": self.dependencies,
            "atlas_version": self.atlas_version,
            "permissions": self.permissions,
            "config_schema": self.config_schema,
        }


@dataclass
class PluginInfo:
    """Information about a discovered plugin."""
    manifest: PluginManifest
    path: Path
    enabled: bool = False
    loaded: bool = False
    error: str | None = None


class PluginManager:
    """Manages plugin discovery, loading, and lifecycle.

    Permission enforcement (v1.3.0):
        Plugins declare required permissions in their manifest.
        Permissions are registered on load and enforced via check_permission().
        NOTE: v1.3.0 enforcement is software-level only (in-process).
        OS-level sandboxing is planned for v1.4.0.
    """

    def __init__(self, plugins_dir: str | Path = "./plugins") -> None:
        self.plugins_dir = Path(plugins_dir)
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self._plugins: dict[str, PluginInfo] = {}
        self._enabled_file = self.plugins_dir / ".enabled"
        self._permissions: PermissionRegistry = get_permission_registry()
        self._load_enabled_state()

    def _load_enabled_state(self) -> None:
        """Load enabled plugins from state file."""
        if self._enabled_file.exists():
            try:
                with self._enabled_file.open("r") as f:
                    enabled = json.load(f)
                for name in enabled:
                    if name in self._plugins:
                        self._plugins[name].enabled = True
            except Exception as exc:
                logger.warning("Failed to load enabled plugins: %s", exc)

    def _save_enabled_state(self) -> None:
        """Save enabled plugins to state file."""
        enabled = [name for name, info in self._plugins.items() if info.enabled]
        try:
            with self._enabled_file.open("w") as f:
                json.dump(enabled, f)
        except Exception as exc:
            logger.warning("Failed to save enabled plugins: %s", exc)

    def discover(self) -> dict[str, PluginInfo]:
        """Discover all plugins in plugins_dir."""
        self._plugins.clear()

        for item in self.plugins_dir.iterdir():
            if item.is_dir():
                manifest_path = item / "atlas-plugin.yaml"
                if manifest_path.exists():
                    try:
                        manifest = PluginManifest.from_yaml(manifest_path)
                        enabled = False
                        self._plugins[manifest.name] = PluginInfo(
                            manifest=manifest,
                            path=item,
                            enabled=enabled,
                        )
                    except Exception as exc:
                        logger.warning("Failed to load plugin from %s: %s", item, exc)

        self._load_enabled_state()
        return self._plugins

    def get(self, name: str) -> PluginInfo | None:
        """Get plugin info by name."""
        return self._plugins.get(name)

    def list_all(self) -> list[PluginInfo]:
        """List all discovered plugins."""
        return list(self._plugins.values())

    def list_enabled(self) -> list[PluginInfo]:
        """List enabled plugins."""
        return [p for p in self._plugins.values() if p.enabled]

    def enable(self, name: str) -> bool:
        """Enable a plugin."""
        plugin = self._plugins.get(name)
        if not plugin:
            return False
        plugin.enabled = True
        self._save_enabled_state()
        return True

    def disable(self, name: str) -> bool:
        """Disable a plugin."""
        plugin = self._plugins.get(name)
        if not plugin:
            return False
        plugin.enabled = False
        plugin.loaded = False
        self._save_enabled_state()
        return True

    async def load_plugin(self, name: str, app: Any = None) -> Any:
        """Load and initialize a plugin.

        Registers the plugin's declared permissions in the PermissionRegistry
        after successful initialization. Permission checks are software-level
        only in v1.3.0 (in-process plugins).
        """
        plugin = self._plugins.get(name)
        if not plugin:
            raise ValueError(f"Plugin '{name}' not found")

        if not plugin.enabled:
            raise ValueError(f"Plugin '{name}' is not enabled")

        if plugin.loaded:
            return plugin.path

        # Add plugin directory to Python path
        plugin_path = plugin.path
        if str(plugin_path) not in sys.path:
            sys.path.insert(0, str(plugin_path))

        # Install dependencies
        await self._install_dependencies(plugin.manifest.dependencies)

        # Load the plugin module
        entry_point = plugin.manifest.entry_point
        if ":" in entry_point:
            module_name, class_name = entry_point.split(":", 1)
        else:
            module_name, class_name = entry_point, "Plugin"

        try:
            unique_name = f"atlas.plugins.{name}.{module_name}"
            spec = importlib.util.spec_from_file_location(
                unique_name, plugin_path / f"{module_name}.py"
            )
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load module {module_name} from {plugin_path}")

            module = importlib.util.module_from_spec(spec)
            module.__package__ = f"atlas.plugins.{name}"
            sys.modules[unique_name] = module
            spec.loader.exec_module(module)

            plugin_class = getattr(module, class_name)
            plugin_instance = plugin_class()

            # Initialize if it has an initialize method
            if hasattr(plugin_instance, "initialize"):
                if app:
                    await plugin_instance.initialize(app)
                else:
                    await plugin_instance.initialize()

            plugin.loaded = True

            # Register declared permissions AFTER successful load
            self._permissions.register(name, plugin.manifest.permissions)
            if plugin.manifest.permissions:
                logger.info(
                    "Plugin '%s' granted permissions: %s",
                    name, plugin.manifest.permissions,
                )
            else:
                logger.info(
                    "Plugin '%s' loaded with no permissions declared "
                    "(in-process; v1.4.0 will enforce stricter defaults)",
                    name,
                )

            return plugin_instance

        except Exception as exc:
            plugin.error = str(exc)
            logger.exception("Failed to load plugin '%s'", name)
            raise

    def check_plugin_permission(self, plugin_name: str, permission: Permission) -> None:
        """Check if a plugin has the required permission.

        Plugin code should call this before accessing protected resources::

            manager.check_plugin_permission("my-plugin", Permission.NETWORK)

        Raises:
            PermissionDeniedError: If the plugin lacks the declared permission.
        """
        self._permissions.check(plugin_name, permission)

    def get_plugin_permissions(self, plugin_name: str) -> list[str]:
        """Return the list of permissions granted to a plugin."""
        return self._permissions.list_grants(plugin_name)

    async def unload_plugin(self, name: str) -> None:
        """Unload a plugin and revoke its permissions."""
        plugin = self._plugins.get(name)
        if not plugin or not plugin.loaded:
            return

        # Try to call shutdown if available
        # Note: In a real implementation, we'd keep reference to instance
        plugin.loaded = False
        # Revoke all permissions granted to this plugin
        self._permissions.unregister(name)
        logger.info("Plugin '%s' unloaded", name)

    async def _install_dependencies(self, dependencies: list[str]) -> None:
        """Install plugin dependencies via pip."""
        if not dependencies:
            return

        for dep in dependencies:
            try:
                logger.info("Installing plugin dependency: %s", dep)
                proc = await asyncio.create_subprocess_exec(
                    get_python_executable(), "-m", "pip", "install", dep,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
                if proc.returncode != 0:
                    logger.warning("Failed to install dependency: %s", dep)
            except Exception as exc:
                logger.warning("Error installing dependency %s: %s", dep, exc)

    def install_from_zip(self, zip_path: str | Path) -> PluginInfo:
        """Install a plugin from a zip file."""
        zip_path = Path(zip_path)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmpdir_path)

            # Find manifest
            manifest_path = tmpdir_path / "atlas-plugin.yaml"
            if not manifest_path.exists():
                raise ValueError("No atlas-plugin.yaml found in package")

            manifest = PluginManifest.from_yaml(manifest_path)
            target_dir = self.plugins_dir / manifest.name

            if target_dir.exists():
                shutil.rmtree(target_dir)

            shutil.copytree(tmpdir_path, target_dir)

            plugin_info = PluginInfo(
                manifest=manifest,
                path=target_dir,
                enabled=False,
            )
            self._plugins[manifest.name] = plugin_info
            logger.info("Installed plugin '%s' from %s", manifest.name, zip_path)
            return plugin_info

    def uninstall(self, name: str) -> bool:
        """Uninstall a plugin."""
        plugin = self._plugins.get(name)
        if not plugin:
            return False

        if plugin.loaded:
            raise ValueError(f"Plugin '{name}' is currently loaded. Disable first.")

        shutil.rmtree(plugin.path, ignore_errors=True)
        del self._plugins[name]
        self._save_enabled_state()
        logger.info("Uninstalled plugin '%s'", name)
        return True

    def create_plugin_template(self, name: str, path: str | Path | None = None) -> Path:
        """Create a new plugin template."""
        if path is None:
            path = self.plugins_dir / name
        else:
            path = Path(path)

        path.mkdir(parents=True, exist_ok=True)

        # Create manifest
        manifest = PluginManifest(
            name=name,
            version="0.1.0",
            description=f"{name} plugin for Atlas OS",
            author="Atlas OS Developer",
            entry_point="main:Plugin",
            dependencies=[],
            permissions=[],
        )

        manifest_path = path / "atlas-plugin.yaml"
        with manifest_path.open("w") as f:
            yaml.dump(manifest.to_dict(), f, default_flow_style=False, sort_keys=False)

        # Create main module
        main_py = path / "main.py"
        main_content = f'''"""Plugin: {name}"""

from __future__ import annotations

from typing import Any


class Plugin:
    """Plugin entry point for Atlas OS."""

    def __init__(self) -> None:
        self.name = "{name}"
        self.version = "0.1.0"

    async def initialize(self, app: Any = None) -> None:
        """Initialize the plugin."""
        print(f"Initializing {{self.name}} plugin")

    async def shutdown(self) -> None:
        """Shutdown the plugin."""
        print(f"Shutting down {{self.name}} plugin")

    def get_commands(self) -> list:
        """Return Click command groups for CLI integration."""
        return []
'''

        main_py.write_text(main_content)

        # Create __init__.py
        init_py = path / "__init__.py"
        init_py.write_text('__version__ = "0.1.0"\n')

        # Create README
        readme = path / "README.md"
        readme.write_text(f"# {name}\n\nAtlas OS Plugin\n")

        logger.info("Created plugin template at %s", path)
        return path