"""Base classes and registry for Atlas OS AI tools."""

from __future__ import annotations

import inspect
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


class ToolPermissionLevel(str, Enum):
    """Authorization permission level for OS tools."""
    READ_ONLY = "read_only"                  # Low risk, automatic execution
    CONFIRMATION_REQUIRED = "confirmation"   # Mutating action, user approval needed
    ADMIN = "admin"                          # High risk system change


@dataclass
class ToolParameter:
    """Description of a tool parameter."""
    name: str
    param_type: str
    description: str
    required: bool = True
    default: Any = None


@dataclass
class ToolResult:
    """Execution result from an OS tool."""
    success: bool
    data: Any
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
        }


class BaseTool(ABC):
    """Abstract base class for all Atlas OS AI tools."""

    name: str
    description: str
    permission_level: ToolPermissionLevel = ToolPermissionLevel.READ_ONLY
    parameters: list[ToolParameter] = []

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool action."""

    def to_schema(self) -> dict[str, Any]:
        """Generate OpenAI/Gemini compatible tool function definition."""
        properties: dict[str, Any] = {}
        required_params: list[str] = []

        for p in self.parameters:
            properties[p.name] = {
                "type": p.param_type,
                "description": p.description,
            }
            if p.required:
                required_params.append(p.name)

        return {
            "name": self.name,
            "description": self.description,
            "permission_level": self.permission_level.value,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required_params,
            },
        }


class ToolRegistry:
    """Catalog and executor for registered Atlas OS AI tools."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a new tool."""
        self._tools[tool.name] = tool
        logger.debug("ToolRegistry: registered tool '%s'", tool.name)

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[BaseTool]:
        """Return all registered tools."""
        return list(self._tools.values())

    def get_schemas(self) -> list[dict[str, Any]]:
        """Get schemas of all registered tools."""
        return [t.to_schema() for t in self._tools.values()]

    async def execute(self, name: str, **kwargs: Any) -> ToolResult:
        """Execute a tool by name with arguments."""
        tool = self.get(name)
        if tool is None:
            return ToolResult(
                success=False,
                data=None,
                error=f"Tool '{name}' not found in registry.",
            )

        try:
            return await tool.execute(**kwargs)
        except Exception as exc:
            logger.exception("Error executing tool '%s': %s", name, exc)
            return ToolResult(
                success=False,
                data=None,
                error=f"Tool '{name}' failed: {exc}",
            )
