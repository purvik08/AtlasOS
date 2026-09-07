"""Integration tests for AtlasOS FastAPI endpoints."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from atlas.api import create_api_app
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
    atlas_app = AtlasApplication(config)
    return atlas_app


@pytest.fixture
def fastapi_app(app):
    return create_api_app(app)


@pytest.fixture
async def client(fastapi_app, app):
    # Initialize AI manager in app
    ai_mgr = app.container.resolve("ai_manager")
    await ai_mgr.start()
    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app), base_url="http://test"
    ) as ac:
        yield ac
    await ai_mgr.stop()


class TestApiRoutes:
    """Test REST API endpoints."""

    async def test_health(self, client: AsyncClient):
        response = await client.get("/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    async def test_system_info(self, client: AsyncClient):
        response = await client.get("/v1/system/info")
        assert response.status_code == 200
        data = response.json()
        assert "hostname" in data
        assert "cpu_percent" in data
        assert "memory_percent" in data
        assert "disk_percent" in data
        assert "runtime_state" in data

    async def test_models_list(self, client: AsyncClient):
        response = await client.get("/v1/models")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_providers_list(self, client: AsyncClient):
        response = await client.get("/v1/providers")
        assert response.status_code == 200
        providers = response.json()
        assert len(providers) > 0
        names = [p["name"] for p in providers]
        assert "llama_cpp" in names

    async def test_network_status(self, client: AsyncClient):
        response = await client.get("/v1/network/status")
        assert response.status_code == 200
        data = response.json()
        assert "connected" in data
        assert "interfaces" in data

    async def test_voice_status(self, client: AsyncClient):
        response = await client.get("/v1/voice/status")
        assert response.status_code == 200
        data = response.json()
        assert "audio" in data

    async def test_memory_crud(self, client: AsyncClient):
        # 1. Remember
        rem_res = await client.post(
            "/v1/memory/remember",
            json={"text": "AtlasOS is an edge AI operating system.", "category": "fact"},
        )
        assert rem_res.status_code == 200
        data = rem_res.json()
        assert data["success"] is True
        mem_id = data["id"]

        # 2. List
        list_res = await client.get("/v1/memory/list")
        assert list_res.status_code == 200
        assert list_res.json()["count"] >= 1

        # 3. Recall
        rec_res = await client.post(
            "/v1/memory/recall",
            json={"query": "edge AI", "top_k": 5},
        )
        assert rec_res.status_code == 200
        assert "results" in rec_res.json()

        # 4. Delete
        del_res = await client.delete(f"/v1/memory/{mem_id}")
        assert del_res.status_code == 200
        assert del_res.json()["success"] is True

    async def test_plugins_list(self, client: AsyncClient):
        response = await client.get("/v1/plugins")
        assert response.status_code == 200
        data = response.json()
        assert "plugins" in data

    async def test_terminal_ping(self, client: AsyncClient):
        response = await client.get("/v1/terminal/ping")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "platform" in data

    async def test_web_ui_endpoint(self, client: AsyncClient):
        response = await client.get("/ui")
        assert response.status_code == 200
        assert "Atlas OS" in response.text
