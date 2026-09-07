"""Unit and integration tests for Atlas OS AI layer and tools."""

from __future__ import annotations

import pytest

from atlas.ai.os_ai import AtlasOSAI
from atlas.ai.tools import create_default_tool_registry
from atlas.ai.tools.base import ToolPermissionLevel, ToolRegistry, ToolResult
from atlas.ai.tools.system_tools import GetSystemInfoTool, GetSystemMetricsTool
from atlas.rag.service import RAGService


@pytest.mark.asyncio
async def test_system_tools():
    metrics_tool = GetSystemMetricsTool()
    res = await metrics_tool.execute()
    assert res.success is True
    assert "cpu_percent" in res.data
    assert "ram_percent" in res.data
    assert "uptime" in res.data

    info_tool = GetSystemInfoTool()
    info_res = await info_tool.execute()
    assert info_res.success is True
    assert info_res.data["os"] == "Atlas OS"


@pytest.mark.asyncio
async def test_tool_registry():
    registry = create_default_tool_registry()
    schemas = registry.get_schemas()
    assert len(schemas) >= 8

    # Test tool lookup and execution
    tool = registry.get("get_system_metrics")
    assert tool is not None
    assert tool.permission_level == ToolPermissionLevel.READ_ONLY

    res = await registry.execute("get_system_metrics")
    assert res.success is True


@pytest.mark.asyncio
async def test_os_ai_direct_intent_resolution(tmp_path):
    rag_dir = tmp_path / "rag_data"
    rag_svc = RAGService(data_dir=rag_dir)
    os_ai = AtlasOSAI(rag_service=rag_svc)

    # 1. Test system metrics intent
    res = await os_ai.process_message("What is my current RAM usage?")
    assert "RAM Usage:" in res.content
    assert res.tool_used == "get_system_metrics"

    # 2. Test system info intent
    info_res = await os_ai.process_message("Show system info")
    assert "Atlas OS" in info_res.content
    assert info_res.tool_used == "get_system_info"

    # 3. Test models query intent
    models_res = await os_ai.process_message("What models are installed?")
    assert models_res.tool_used == "list_models"

    # 4. Test wifi status intent
    wifi_res = await os_ai.process_message("What is my wifi status?")
    assert wifi_res.tool_used == "get_network_status"


@pytest.mark.asyncio
async def test_os_ai_rag_retrieval_and_context(tmp_path):
    rag_dir = tmp_path / "rag_data"
    rag_svc = RAGService(data_dir=rag_dir)
    rag_svc.ingest_text(
        text="Atlas OS uses an explicit dependency injection container for all service resolutions.",
        title="Architecture Guide",
    )

    os_ai = AtlasOSAI(rag_service=rag_svc)

    # Explicit search intent
    search_res = await os_ai.process_message("Search documents for dependency injection")
    assert search_res.tool_used == "search_knowledge"
    assert "Architecture Guide" in search_res.content


@pytest.mark.asyncio
async def test_os_ai_streaming(tmp_path):
    rag_dir = tmp_path / "rag_data"
    rag_svc = RAGService(data_dir=rag_dir)
    os_ai = AtlasOSAI(rag_service=rag_svc)

    tokens = []
    async for chunk in os_ai.process_stream("What is the system uptime?"):
        tokens.append(chunk)

    full_text = "".join(tokens)
    assert "System Uptime" in full_text
