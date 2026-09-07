"""Unit tests for AtlasSDK methods."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from atlas.api import create_api_app
from atlas.api.sdk import AtlasSDK
from atlas.config.settings import AtlasConfig
from atlas.runtime.application import AtlasApplication


@pytest.fixture
def app(tmp_path):
    config = AtlasConfig(
        data_dir=str(tmp_path / "data"),
        models_dir=str(tmp_path / "models"),
        plugins_dir=str(tmp_path / "plugins"),
    )
    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "models").mkdir(exist_ok=True)
    (tmp_path / "plugins").mkdir(exist_ok=True)
    return AtlasApplication(config)


@pytest.fixture
def fastapi_app(app):
    return create_api_app(app)


@pytest.fixture
async def sdk(fastapi_app, app):
    ai_mgr = app.container.resolve("ai_manager")
    await ai_mgr.start()

    sdk_instance = AtlasSDK(base_url="http://test")
    # Inject ASGI transport client
    sdk_instance._client = AsyncClient(
        transport=ASGITransport(app=fastapi_app), base_url="http://test"
    )
    yield sdk_instance
    await sdk_instance.close()
    await ai_mgr.stop()


class TestSdkMethods:
    """Test all AtlasSDK operations."""

    async def test_sdk_health(self, sdk: AtlasSDK):
        res = await sdk.health()
        assert "status" in res

    async def test_sdk_list_models(self, sdk: AtlasSDK):
        res = await sdk.list_models()
        assert isinstance(res, list)

    async def test_sdk_list_providers(self, sdk: AtlasSDK):
        res = await sdk.list_providers()
        assert len(res) > 0

    async def test_sdk_network_status(self, sdk: AtlasSDK):
        res = await sdk.network_status()
        assert "connected" in res

    async def test_sdk_voice_status(self, sdk: AtlasSDK):
        res = await sdk.voice_status()
        assert "audio" in res

    async def test_sdk_voice_devices(self, sdk: AtlasSDK):
        res = await sdk.voice_devices()
        assert "inputs" in res
        assert "outputs" in res

    async def test_sdk_memory_operations(self, sdk: AtlasSDK):
        # 1. Remember
        rem = await sdk.remember_memory("Test memory fact", "test", "user")
        assert rem["success"] is True
        mem_id = rem["id"]

        # 2. List
        lst = await sdk.list_memories()
        assert lst["count"] >= 1

        # 3. Recall
        rec = await sdk.recall_memories("Test memory")
        assert "results" in rec

        # 4. Delete
        d = await sdk.delete_memory(mem_id)
        assert d["success"] is True

    async def test_sdk_plugins(self, sdk: AtlasSDK):
        res = await sdk.list_plugins()
        assert "plugins" in res
