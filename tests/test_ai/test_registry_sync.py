"""Integration tests for ModelRegistry persistence and cross-process state synchronization."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from atlas.ai.manager import AIManager
from atlas.ai.providers.base import ProviderStatus
from atlas.config.settings import AtlasConfig


def _make_config(tmp_path: Path) -> AtlasConfig:
    models_dir = tmp_path / "models"
    data_dir = tmp_path / "data"
    models_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    return AtlasConfig(
        models_dir=str(models_dir),
        data_dir=str(data_dir),
        health_check_interval_seconds=60,
        heartbeat_interval_seconds=60,
        graceful_shutdown_timeout_seconds=2,
    )


@pytest.mark.asyncio
async def test_download_persists_model_state_across_instances(tmp_path):
    """Verify downloading a model in instance 1 makes it visible in a fresh instance 2."""
    config = _make_config(tmp_path)

    # Process 1: Download a model
    mgr1 = AIManager(config)
    await mgr1.start()

    # Create dummy local file as if downloaded
    dest_path = Path(config.models_dir) / "llama-2-7b.Q4_K_M.gguf"
    dest_path.write_bytes(b"GGUF_TEST_DATA" * 10)

    # Trigger registry scan / register
    mgr1.model_registry.scan(config.models_dir)
    await mgr1.stop()

    # Process 2: Fresh instance (simulating separate CLI process execution)
    mgr2 = AIManager(config)
    await mgr2.start()
    try:
        models = mgr2.list_models()
        model_ids = [m.model_id for m in models]
        assert "llama-2-7b.Q4_K_M" in model_ids

        m_info = mgr2.model_registry.get("llama-2-7b.Q4_K_M")
        assert m_info.loaded is False
        assert m_info.provider_name == "llama_cpp"
    finally:
        await mgr2.stop()


@pytest.mark.asyncio
async def test_load_and_unload_synchronizes_state_across_instances(tmp_path):
    """Verify loading in instance 1 updates loaded status in fresh
    instance 2, and unloading syncs as well."""
    config = _make_config(tmp_path)

    # Process 1: Setup model file
    mgr1 = AIManager(config)
    await mgr1.start()

    dest_path = Path(config.models_dir) / "test-model.gguf"
    dest_path.write_bytes(b"GGUF_DATA" * 10)
    mgr1.model_registry.scan(config.models_dir)

    # Mock llama_cpp load and load model in Process 1 (simulating CLI process exit)
    mock_instance = MagicMock()
    with patch("atlas.ai.providers.llama_cpp.llama_cpp") as mock_llama_cpp, \
         patch.object(mgr1.resource_manager, "check_allocation_safety"):
        mock_llama_cpp.Llama.return_value = mock_instance
        await mgr1.load_model("test-model")

    assert mgr1.model_registry.get("test-model").loaded is True

    # Process 2: Fresh instance reads persisted state
    mgr2 = AIManager(config)
    await mgr2.start()
    try:
        # Check model list in instance 2
        info = mgr2.model_registry.get("test-model")
        assert info.loaded is True

        # Check provider health in instance 2
        health = await mgr2.provider_health("llama_cpp")
        assert health.status is ProviderStatus.HEALTHY
        assert "test-model" in health.loaded_models

        # Now unload model in Process 2
        await mgr2.unload_model("test-model")
        assert mgr2.model_registry.get("test-model").loaded is False
    finally:
        await mgr2.stop()

    # Process 3: Fresh instance verifies unloaded state
    mgr3 = AIManager(config)
    await mgr3.start()
    try:
        info3 = mgr3.model_registry.get("test-model")
        assert info3.loaded is False

        health3 = await mgr3.provider_health("llama_cpp")
        assert health3.status is ProviderStatus.UNLOADED
        assert "test-model" not in health3.loaded_models
    finally:
        await mgr3.stop()


@pytest.mark.asyncio
async def test_cloud_providers_do_not_report_loaded_unloaded(tmp_path):
    """Verify cloud providers do not report local Loaded/Unloaded RAM state."""
    config = _make_config(tmp_path)
    mgr = AIManager(config)
    
    # Clear any stored API keys to test truly unconfigured providers
    from atlas.secrets import delete_api_key
    for provider in ["gemini", "deepseek", "kimi", "qwen"]:
        delete_api_key(provider)
    
    await mgr.start()
    try:
        # Gemini with empty key should report UNHEALTHY status and empty loaded_models
        g_health = await mgr.provider_health("gemini")
        assert g_health.status is ProviderStatus.UNHEALTHY
        assert g_health.loaded_models == []
        assert "No API key" in g_health.message

        # DeepSeek with empty key
        d_health = await mgr.provider_health("deepseek")
        assert d_health.status is ProviderStatus.UNHEALTHY
        assert d_health.loaded_models == []
    finally:
        await mgr.stop()
