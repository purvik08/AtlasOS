"""Plugin inspection tools for Atlas OS AI."""

from __future__ import annotations

import logging
from typing import Any

from atlas.ai.tools.base import BaseTool, ToolPermissionLevel, ToolResult

logger = logging.getLogger(__name__)


class ListPluginsTool(BaseTool):
    """List discovered Atlas plugins without executing them."""

    name = "list_plugins"
    description = "List installed Atlas OS plugins, versions, enabled state, and declared permissions."
    permission_level = ToolPermissionLevel.READ_ONLY
    parameters = []

    def __init__(self, plugin_manager: Any | None = None) -> None:
        self.plugin_manager = plugin_manager

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            manager = self.plugin_manager
            if manager is None:
                from atlas.plugins.core import PluginManager

                manager = PluginManager()
            plugins = manager.discover()
            data = [
                {
                    "name": p.manifest.name,
                    "version": p.manifest.version,
                    "description": p.manifest.description,
                    "enabled": p.enabled,
                    "loaded": p.loaded,
                    "permissions": p.manifest.permissions,
                }
                for p in plugins.values()
            ]
            return ToolResult(success=True, data=data)
        except Exception as exc:
            return ToolResult(success=False, data=None, error=str(exc))
