"""Plugin permission system for Atlas OS.

v1.3.0: In-process plugins with software-level permission checks.

IMPORTANT SECURITY NOTE:
    These checks are software-level enforcement only. v1.3.0 plugins run
    in-process and are trusted code. Permission checks prevent accidental
    misuse and prepare the architecture for OS-level sandboxing in v1.4.0.
    They do NOT provide OS-level isolation (no seccomp, Firejail, containers).

Architecture:
    Plugin manifest declares required permissions:
        permissions: ["network", "filesystem.read"]

    PluginManager registers these on load.
    Plugin code calls check_permission() before accessing protected resources.
    Unauthorized access raises PermissionDeniedError and is logged.

Future (v1.4.0):
    Process isolation can be added by wrapping plugin execution in a
    subprocess/container while preserving this permission API.
"""

from __future__ import annotations

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """Declared plugin capability permissions.

    Plugins must list required permissions in their ``atlas-plugin.yaml``
    under the ``permissions:`` key. Accessing resources without declaring
    the required permission raises ``PermissionDeniedError``.
    """
    # File system
    FILESYSTEM_READ  = "filesystem.read"
    FILESYSTEM_WRITE = "filesystem.write"

    # Network
    NETWORK = "network"

    # Audio
    AUDIO = "audio"

    # AI inference (local and cloud)
    AI_INFERENCE = "ai.inference"

    # System administration
    SYSTEM_ADMIN = "system.admin"

    # Memory access
    MEMORY_READ  = "memory.read"
    MEMORY_WRITE = "memory.write"

    # MQTT pub/sub
    MQTT = "mqtt"

    # Plugin management (install/remove other plugins)
    PLUGIN_MANAGE = "plugin.manage"


class PermissionDeniedError(PermissionError):
    """Raised when a plugin attempts to use an undeclared permission."""

    def __init__(self, plugin_name: str, permission: Permission) -> None:
        self.plugin_name = plugin_name
        self.permission = permission
        super().__init__(
            f"Plugin '{plugin_name}' attempted to use undeclared permission "
            f"'{permission.value}'. "
            f"Add '{permission.value}' to the plugin's manifest permissions list."
        )


class PermissionRegistry:
    """Registry of granted permissions per plugin.

    The PluginManager populates this on plugin load from the manifest.
    Plugin code calls ``check()`` before accessing protected resources.
    """

    def __init__(self) -> None:
        self._grants: dict[str, set[Permission]] = {}

    def register(self, plugin_name: str, permissions: list[str]) -> None:
        """Register permissions granted to a plugin (called by PluginManager).

        Args:
            plugin_name:  Plugin identifier (from manifest ``name``).
            permissions:  List of permission strings from the manifest.
        """
        granted: set[Permission] = set()
        for p in permissions:
            try:
                granted.add(Permission(p))
            except ValueError:
                logger.warning(
                    "Plugin '%s' declared unknown permission '%s' — ignored",
                    plugin_name, p,
                )
        self._grants[plugin_name] = granted
        logger.debug(
            "Registered %d permission(s) for plugin '%s': %s",
            len(granted), plugin_name, [p.value for p in granted],
        )

    def unregister(self, plugin_name: str) -> None:
        """Remove all permission grants for a plugin (called on unload)."""
        self._grants.pop(plugin_name, None)

    def has_permission(self, plugin_name: str, permission: Permission) -> bool:
        """Return True if ``plugin_name`` has been granted ``permission``."""
        return permission in self._grants.get(plugin_name, set())

    def check(self, plugin_name: str, permission: Permission) -> None:
        """Assert that a plugin has the required permission.

        Logs a violation and raises ``PermissionDeniedError`` if denied.

        Args:
            plugin_name: The calling plugin's name.
            permission:  The permission being requested.

        Raises:
            PermissionDeniedError: If the plugin has not declared this permission.
        """
        if not self.has_permission(plugin_name, permission):
            logger.error(
                "PERMISSION VIOLATION: plugin '%s' tried to access '%s' "
                "without declaring it in the manifest.",
                plugin_name, permission.value,
            )
            raise PermissionDeniedError(plugin_name, permission)

    def list_grants(self, plugin_name: str) -> list[str]:
        """Return the list of permission values granted to a plugin."""
        return [p.value for p in self._grants.get(plugin_name, set())]


# ---------------------------------------------------------------------------
# Module-level singleton registry (used by PluginManager)
# ---------------------------------------------------------------------------
_registry = PermissionRegistry()


def get_permission_registry() -> PermissionRegistry:
    """Return the global PermissionRegistry singleton."""
    return _registry


def check_permission(plugin_name: str, permission: Permission) -> None:
    """Convenience wrapper: check a permission in the global registry.

    Plugin code should use this to gate access to protected resources::

        from atlas.plugins.permissions import check_permission, Permission

        check_permission("my-plugin", Permission.NETWORK)
        # ... proceed with network call ...

    Raises:
        PermissionDeniedError: If the plugin lacks the declared permission.
    """
    _registry.check(plugin_name, permission)
