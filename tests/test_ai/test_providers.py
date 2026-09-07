"""Tests for all provider stubs — interface compliance and behaviour."""

from __future__ import annotations

import pytest

from atlas.ai.providers.base import (
    AIProvider,
    Message,
    MessageRole,
    ProviderRole,
    ProviderStatus,
)
from atlas.ai.providers.deepseek import DeepSeekProvider
from atlas.ai.providers.gemini import GeminiProvider
from atlas.ai.providers.kimi import KimiProvider
from atlas.ai.providers.llama_cpp import LlamaCppProvider
from atlas.ai.providers.qwen import QwenProvider

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def llama(tmp_path):
    return LlamaCppProvider(models_dir=tmp_path)


@pytest.fixture
def gemini_no_key():
    return GeminiProvider(api_key="")


@pytest.fixture
def gemini_with_key():
    return GeminiProvider(api_key="test-key-123")


@pytest.fixture
def deepseek():
    return DeepSeekProvider(api_key="")


@pytest.fixture
def kimi():
    return KimiProvider(api_key="")


@pytest.fixture
def qwen():
    return QwenProvider(api_key="")


@pytest.fixture
def user_message():
    return Message(role=MessageRole.USER, content="Hello, Atlas!")


# ---------------------------------------------------------------------------
# Interface compliance — every provider must pass these
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "provider_fixture",
    ["llama", "gemini_no_key", "deepseek", "kimi", "qwen"],
)
async def test_provider_is_airovider_subclass(request, provider_fixture):
    provider = request.getfixturevalue(provider_fixture)
    assert isinstance(provider, AIProvider)


@pytest.mark.parametrize(
    "provider_fixture",
    ["llama", "gemini_no_key", "deepseek", "kimi", "qwen"],
)
async def test_provider_has_name_and_role(request, provider_fixture):
    provider = request.getfixturevalue(provider_fixture)
    assert isinstance(provider.name, str) and provider.name
    assert isinstance(provider.role, ProviderRole)


@pytest.mark.parametrize(
    "provider_fixture",
    ["llama", "gemini_no_key", "deepseek", "kimi", "qwen"],
)
async def test_list_models_returns_list(request, provider_fixture):
    provider = request.getfixturevalue(provider_fixture)
    models = await provider.list_models()
    assert isinstance(models, list)
    for m in models:
        assert m.provider_name == provider.name


@pytest.mark.parametrize(
    "provider_fixture",
    ["gemini_no_key", "deepseek", "kimi", "qwen"],
)
async def test_chat_returns_chat_response(request, provider_fixture, user_message):
    provider = request.getfixturevalue(provider_fixture)
    models = await provider.list_models()
    model_id = models[0].model_id if models else "test-model"
    response = await provider.chat([user_message], model_id=model_id)
    assert response.provider_name == provider.name
    assert response.message.role is MessageRole.ASSISTANT
    assert isinstance(response.message.content, str)


async def test_llama_chat_returns_stub_response(llama, user_message):
    response = await llama.chat([user_message], model_id="nonexistent-model")
    assert response.provider_name == "llama_cpp"
    assert response.message.role is MessageRole.ASSISTANT
    # When no model is loaded, the provider returns an informational fallback message.
    assert "nonexistent-model" in response.message.content or response.message.content


@pytest.mark.parametrize(
    "provider_fixture",
    ["gemini_no_key", "deepseek", "kimi", "qwen"],
)
async def test_stream_chat_yields_strings(request, provider_fixture, user_message):
    provider = request.getfixturevalue(provider_fixture)
    models = await provider.list_models()
    model_id = models[0].model_id if models else "test-model"
    chunks = []
    async for chunk in provider.stream_chat([user_message], model_id=model_id):
        chunks.append(chunk)
        assert isinstance(chunk, str)
    assert chunks, "stream_chat must yield at least one chunk"


async def test_llama_stream_chat_yields_chunks(llama, user_message):
    chunks = []
    async for chunk in llama.stream_chat([user_message], model_id="no-model"):
        chunks.append(chunk)
    assert chunks


# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------


async def test_llama_health_unloaded(llama):
    health = await llama.health()
    assert health.provider_name == "llama_cpp"
    assert health.status is ProviderStatus.UNLOADED


async def test_gemini_health_no_key(gemini_no_key):
    health = await gemini_no_key.health()
    assert health.status is ProviderStatus.UNHEALTHY


async def test_gemini_health_with_key(gemini_with_key):
    health = await gemini_with_key.health()
    assert health.status is ProviderStatus.HEALTHY


async def test_deepseek_health_no_key(deepseek):
    health = await deepseek.health()
    assert health.status is ProviderStatus.UNHEALTHY


# ---------------------------------------------------------------------------
# Load / unload
# ---------------------------------------------------------------------------


async def test_llama_load_unknown_model_raises(llama):
    with pytest.raises(ValueError, match="not found"):
        await llama.load_model("nonexistent-model")


async def test_llama_load_existing_model(tmp_path):
    from unittest.mock import MagicMock, patch

    gguf = tmp_path / "my-model.gguf"
    gguf.write_bytes(b"\x00" * 100)
    provider = LlamaCppProvider(models_dir=tmp_path)

    # Mock llama_cpp.Llama so a dummy .gguf file is accepted without real parsing.
    mock_instance = MagicMock()
    with patch("atlas.ai.providers.llama_cpp.llama_cpp") as mock_llama_cpp:
        mock_llama_cpp.Llama.return_value = mock_instance
        await provider.load_model("my-model")

    health = await provider.health()
    assert "my-model" in health.loaded_models
    assert health.status is ProviderStatus.HEALTHY


async def test_llama_unload_model(tmp_path):
    from unittest.mock import MagicMock, patch

    gguf = tmp_path / "tiny.gguf"
    gguf.write_bytes(b"\x00" * 100)
    provider = LlamaCppProvider(models_dir=tmp_path)

    mock_instance = MagicMock()
    with patch("atlas.ai.providers.llama_cpp.llama_cpp") as mock_llama_cpp:
        mock_llama_cpp.Llama.return_value = mock_instance
        await provider.load_model("tiny")

    await provider.unload_model("tiny")
    health = await provider.health()
    assert "tiny" not in health.loaded_models


async def test_llama_unload_not_loaded_is_noop(llama):
    # Should not raise.
    await llama.unload_model("not-loaded")


async def test_cloud_load_model_raises_actionable_error(gemini_no_key):
    """Cloud model load is rejected with a message that points to API config + health."""
    from atlas.ai.providers.base import ProviderRole

    assert gemini_no_key.role is ProviderRole.CLOUD
    with pytest.raises(ValueError) as excinfo:
        await gemini_no_key.load_model("gemini-1.5-flash")
    msg = str(excinfo.value)
    # Actionable: tells the user what to do (configure API key + health check).
    assert "does not require" in msg or "does not require loading" in msg
    assert "ATLAS_AI__GEMINI_API_KEY" in msg
    assert "atlas provider health gemini" in msg


async def test_cloud_load_unknown_model_mentions_known_models(gemini_no_key):
    """Unknown cloud model IDs are rejected with the set of known model IDs."""
    with pytest.raises(ValueError, match="Unknown Gemini model"):
        await gemini_no_key.load_model("not-a-real-model")


async def test_cloud_unload_model_is_noop(gemini_no_key):
    """Unloading on a cloud provider must be a safe no-op (no local lifecycle)."""
    # Even with nothing loaded, this must not raise.
    await gemini_no_key.unload_model("gemini-1.5-flash")
    health = await gemini_no_key.health()
    assert "gemini-1.5-flash" not in health.loaded_models


# ------------------------------------------------------------------
# Local/cloud separation — OpenAI-compatible clouds (DeepSeek / Qwen / Kimi)
# ------------------------------------------------------------------


@pytest.mark.parametrize(
    "provider_fixture",
    ["deepseek", "kimi", "qwen"],
)
async def test_openai_cloud_load_raises_actionable_error(request, provider_fixture):
    provider = request.getfixturevalue(provider_fixture)
    with pytest.raises(ValueError) as excinfo:
        models = await provider.list_models()
        await provider.load_model(models[0].model_id)
    msg = str(excinfo.value)
    assert "does not require" in msg
    assert "API" in msg
    env_prefix = provider.name.upper()
    assert f"ATLAS_AI__{env_prefix}_API_KEY" in msg
    assert f"atlas provider health {provider.name}" in msg


@pytest.mark.parametrize(
    "provider_fixture",
    ["deepseek", "kimi", "qwen"],
)
async def test_openai_cloud_unknown_model_raises(request, provider_fixture):
    provider = request.getfixturevalue(provider_fixture)
    with pytest.raises(ValueError, match="not-a-real-model"):
        await provider.load_model("not-a-real-model")


# ---------------------------------------------------------------------------
# ProviderInfo descriptor
# ---------------------------------------------------------------------------


async def test_provider_info(gemini_with_key):
    info = gemini_with_key.info()
    assert info.name == "gemini"
    assert info.role is ProviderRole.CLOUD


async def test_llama_provider_info(llama):
    info = llama.info()
    assert info.role is ProviderRole.LOCAL
