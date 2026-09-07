"""Atlas OS AI tools package."""

from __future__ import annotations

from typing import Any

from atlas.ai.tools.base import BaseTool, ToolParameter, ToolPermissionLevel, ToolRegistry, ToolResult
from atlas.ai.tools.model_tools import GetLoadedModelTool, ListModelsTool
from atlas.ai.tools.network_tools import GetNetworkStatusTool, ScanWifiNetworksTool
from atlas.ai.tools.plugin_tools import ListPluginsTool
from atlas.ai.tools.rag_tools import ListKnowledgeDocumentsTool, SearchKnowledgeTool
from atlas.ai.tools.runtime_tools import GetRuntimeStatusTool
from atlas.ai.tools.system_tools import GetSystemInfoTool, GetSystemMetricsTool
from atlas.ai.tools.voice_tools import GetVoiceStatusTool


def _resolve_from_container(container: Any | None, key: str) -> Any | None:
    if container is None:
        return None
    try:
        if key in container:
            return container.resolve(key)
    except Exception:
        return None
    return None


def create_default_tool_registry(
    container: Any | None = None,
    rag_service: Any | None = None,
    model_registry: Any | None = None,
    voice_manager: Any | None = None,
    network_service: Any | None = None,
    plugin_manager: Any | None = None,
) -> ToolRegistry:
    """Instantiate and populate the default tool registry."""
    registry = ToolRegistry()

    if model_registry is None:
        ai_mgr = _resolve_from_container(container, "ai_manager")
        if ai_mgr is not None:
            model_registry = getattr(ai_mgr, "model_registry", None)
    if rag_service is None:
        rag_service = _resolve_from_container(container, "rag_service")
    if network_service is None:
        network_service = _resolve_from_container(container, "network_service")
    if voice_manager is None:
        voice_manager = _resolve_from_container(container, "voice_manager")
    if plugin_manager is None:
        plugin_manager = _resolve_from_container(container, "plugin_manager")

    # System tools
    registry.register(GetSystemMetricsTool())
    registry.register(GetSystemInfoTool())

    # Network tools
    registry.register(GetNetworkStatusTool(network_service=network_service))
    registry.register(ScanWifiNetworksTool(network_service=network_service))

    # Model tools
    registry.register(ListModelsTool(registry=model_registry))
    registry.register(GetLoadedModelTool(registry=model_registry))

    # RAG tools
    registry.register(SearchKnowledgeTool(rag_service=rag_service))
    registry.register(ListKnowledgeDocumentsTool(rag_service=rag_service))

    # Voice tools
    registry.register(GetVoiceStatusTool(voice_manager=voice_manager))

    # Plugin tools
    registry.register(ListPluginsTool(plugin_manager=plugin_manager))

    # Runtime tools
    registry.register(GetRuntimeStatusTool(container=container))

    return registry


__all__ = [
    "BaseTool",
    "ToolParameter",
    "ToolPermissionLevel",
    "ToolResult",
    "ToolRegistry",
    "GetSystemMetricsTool",
    "GetSystemInfoTool",
    "GetNetworkStatusTool",
    "ScanWifiNetworksTool",
    "ListModelsTool",
    "GetLoadedModelTool",
    "SearchKnowledgeTool",
    "ListKnowledgeDocumentsTool",
    "GetVoiceStatusTool",
    "GetRuntimeStatusTool",
    "ListPluginsTool",
    "create_default_tool_registry",
]
