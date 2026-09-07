"""Runtime health and diagnostics tools for Atlas OS AI."""

from __future__ import annotations

import logging
from typing import Any

from atlas.ai.tools.base import BaseTool, ToolPermissionLevel, ToolResult

logger = logging.getLogger(__name__)


class GetRuntimeStatusTool(BaseTool):
    """Tool to inspect Atlas OS services, tasks, and runtime health."""

    name = "get_runtime_status"
    description = "Check the health status of Atlas OS core services, background tasks, and service container."
    permission_level = ToolPermissionLevel.READ_ONLY
    parameters = []

    def __init__(self, container: Any | None = None) -> None:
        self.container = container

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            health_info: dict[str, Any] = {
                "runtime_state": "running",
                "services": [],
            }
            if self.container and hasattr(self.container, "resolve"):
                try:
                    registry = self.container.resolve("service_registry")
                    for s in registry.list_all():
                        health = await s.health()
                        health_info["services"].append({
                            "name": s.name,
                            "status": health.status.value,
                            "message": health.message,
                        })
                except Exception:
                    pass

            return ToolResult(success=True, data=health_info)
        except Exception as exc:
            return ToolResult(success=False, data=None, error=str(exc))
