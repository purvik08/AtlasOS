"""Model management tools for Atlas OS AI."""

from __future__ import annotations

import logging
from typing import Any

from atlas.ai.model import ModelRegistry
from atlas.ai.tools.base import BaseTool, ToolParameter, ToolPermissionLevel, ToolResult

logger = logging.getLogger(__name__)


class ListModelsTool(BaseTool):
    """Tool to list available AI models and their loaded states."""

    name = "list_models"
    description = "List all installed local GGUF models and configured cloud AI models, including sizes and loaded status."
    permission_level = ToolPermissionLevel.READ_ONLY
    parameters = []

    def __init__(self, registry: ModelRegistry | None = None) -> None:
        self.registry = registry

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            registry = self.registry or ModelRegistry(data_dir="./data")
            models = registry.list_all()
            data = [
                {
                    "model_id": m.model_id,
                    "display_name": m.display_name,
                    "provider": m.provider_name,
                    "loaded": m.loaded,
                    "size_mb": round(m.size_bytes / (1024**2), 1) if m.size_bytes > 0 else 0,
                    "description": m.description,
                }
                for m in models
            ]
            return ToolResult(success=True, data=data)
        except Exception as exc:
            return ToolResult(success=False, data=None, error=str(exc))


class GetLoadedModelTool(BaseTool):
    """Tool to inspect which model is currently loaded in memory."""

    name = "get_loaded_model"
    description = "Check which local LLM model is currently active and loaded in system RAM."
    permission_level = ToolPermissionLevel.READ_ONLY
    parameters = []

    def __init__(self, registry: ModelRegistry | None = None) -> None:
        self.registry = registry

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            registry = self.registry or ModelRegistry(data_dir="./data")
            loaded = registry.list_loaded()
            if not loaded:
                return ToolResult(
                    success=True,
                    data={"loaded": False, "message": "No local model is currently loaded in RAM."},
                )
            first = loaded[0]
            return ToolResult(
                success=True,
                data={
                    "loaded": True,
                    "model_id": first.model_id,
                    "display_name": first.display_name,
                    "provider": first.provider_name,
                    "size_mb": round(first.size_bytes / (1024**2), 1) if first.size_bytes > 0 else 0,
                },
            )
        except Exception as exc:
            return ToolResult(success=False, data=None, error=str(exc))
