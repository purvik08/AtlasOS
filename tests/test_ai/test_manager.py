"""Tests for AIManager service lifecycle, session orchestration, provider health, and inference dispatch."""

from __future__ import annotations

import pytest

from atlas.ai.manager import AIManager, SessionNotFoundError
from atlas.ai.providers.base import MessageRole
from atlas.ai.router import ProviderNotFoundError
from atlas.config.settings import AtlasConfig
from atlas.runtime.health import HealthStatus


def _fast_config(tmp_path) -> AtlasConfig:
    return AtlasConfig(
        models_dir=str(tmp_path),
        health_check_interval_seconds=60,
        heartbeat_interval_seconds=60,
        graceful_shutdown_timeout_seconds=2,
    )


@pytest.fixture
async def manager(tmp_path):
    config = _fast_config(tmp_path)
    mgr = AIManager(config)
    await mgr.start()
    try:
        yield mgr
    finally:
        await mgr.stop()


# ---------------------------------------------------------------------------
# Lifecycle and IService compliance
# ---------------------------------------------------------------------------


async def test_manager_name(manager):
    assert manager.name == "ai_manager"


async def test_manager_starts_and_registers_providers(manager):
    providers = manager.list_providers()
    provider_names = [p.name for p in providers]
    assert "llama_cpp" in provider_names
    assert "gemini" in provider_names
    assert "deepseek" in provider_names
    assert "kimi" in provider_names
    assert "qwen" in provider_names


async def test_health_check_healthy(manager):
    health = await manager.health_check()
    assert health.name == "ai_manager"
    # Unhealthy providers (cloud with empty API keys) lead to DEGRADED
    assert health.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)


async def test_health_check_unstarted(tmp_path):
    mgr = AIManager(_fast_config(tmp_path))
    health = await mgr.health_check()
    assert health.status is HealthStatus.UNHEALTHY


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


async def test_new_session_default(manager):
    s = manager.new_session()
    assert s.session_id
    assert s.provider_name == "llama_cpp"  # auto selects local first


async def test_new_session_explicit_provider(manager):
    s = manager.new_session(provider_name="gemini")
    assert s.provider_name == "gemini"


async def test_get_session(manager):
    s = manager.new_session()
    retrieved = manager.get_session(s.session_id)
    assert retrieved.session_id == s.session_id


async def test_get_session_unknown_raises(manager):
    with pytest.raises(SessionNotFoundError):
        manager.get_session("unknown-id")


async def test_delete_session(manager):
    s = manager.new_session()
    manager.delete_session(s.session_id)
    assert len(manager.list_sessions()) == 0


async def test_delete_session_unknown_raises(manager):
    with pytest.raises(SessionNotFoundError):
        manager.delete_session("unknown-id")


# ---------------------------------------------------------------------------
# Inference dispatch (chat & stream_chat)
# ---------------------------------------------------------------------------


async def test_chat(manager):
    s = manager.new_session(provider_name="llama_cpp", model_id="test-m")
    resp = await manager.chat(s.session_id, "Hello!")
    assert resp.provider_name == "llama_cpp"
    assert resp.message.role is MessageRole.ASSISTANT

    # History updated with both user and assistant messages
    msgs = s.get_messages()
    assert len(msgs) == 2
    assert msgs[0].content == "Hello!"
    assert msgs[1].role is MessageRole.ASSISTANT


async def test_chat_unknown_session_raises(manager):
    with pytest.raises(SessionNotFoundError):
        await manager.chat("invalid-session", "Hi")


async def test_stream_chat(manager):
    s = manager.new_session(provider_name="llama_cpp", model_id="test-m")
    chunks = []
    async for chunk in manager.stream_chat(s.session_id, "Stream this"):
        chunks.append(chunk)

    assert len(chunks) > 0
    full_text = "".join(chunks)

    # History updated after stream finishes
    msgs = s.get_messages()
    assert len(msgs) == 2
    assert msgs[1].content == full_text


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


async def test_list_models(manager):
    models = manager.list_models()
    assert isinstance(models, list)
    assert len(models) > 0


async def test_load_and_unload_model(manager, tmp_path):
    gguf = tmp_path / "custom.gguf"
    gguf.write_bytes(b"\x00" * 10)
    manager.model_registry.scan(tmp_path)

    await manager.load_model("custom")
    assert manager.model_registry.get("custom").loaded is True

    await manager.unload_model("custom")
    assert manager.model_registry.get("custom").loaded is False
