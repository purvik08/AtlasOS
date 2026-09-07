"""Atlas OS Python SDK."""

from __future__ import annotations

from typing import Any

import httpx


class AtlasSDK:
    """Python SDK for Atlas OS API."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers: dict[str, str] = {}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers=headers,
                timeout=self._timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> AtlasSDK:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Health & System
    # ------------------------------------------------------------------
    async def health(self) -> dict[str, Any]:
        response = await self._get_client().get("/v1/health")
        response.raise_for_status()
        return response.json()

    async def ready(self) -> dict[str, Any]:
        response = await self._get_client().get("/v1/ready")
        response.raise_for_status()
        return response.json()

    async def system_info(self) -> dict[str, Any]:
        response = await self._get_client().get("/v1/system/info")
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------
    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        top_p: float = 0.95,
        stream: bool = False,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": stream,
            "session_id": session_id,
        }
        response = await self._get_client().post("/v1/chat/completions", json=payload)
        response.raise_for_status()
        return response.json()

    async def stream_chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        top_p: float = 0.95,
        session_id: str | None = None,
    ) -> Any:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": True,
            "session_id": session_id,
        }
        async with self._get_client().stream(
            "POST", "/v1/chat/completions/stream", json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    import json
                    yield json.loads(data)

    # ------------------------------------------------------------------
    # Models
    # ------------------------------------------------------------------
    async def list_models(
        self,
        provider: str | None = None,
        loaded_only: bool = False,
    ) -> list[dict[str, Any]]:
        params: dict[str, str] = {}
        if provider:
            params["provider"] = provider
        if loaded_only:
            params["loaded_only"] = "true"
        response = await self._get_client().get("/v1/models", params=params)
        response.raise_for_status()
        return response.json()

    async def get_model(self, model_id: str) -> dict[str, Any]:
        response = await self._get_client().get(f"/v1/models/{model_id}")
        response.raise_for_status()
        return response.json()

    async def load_model(self, model_id: str, provider: str | None = None) -> dict[str, Any]:
        payload: dict[str, str | None] = {"model_id": model_id}
        if provider:
            payload["provider"] = provider
        response = await self._get_client().post(f"/v1/models/{model_id}/load", json=payload)
        response.raise_for_status()
        return response.json()

    async def unload_model(self, model_id: str, provider: str | None = None) -> dict[str, Any]:
        payload: dict[str, str | None] = {"model_id": model_id}
        if provider:
            payload["provider"] = provider
        response = await self._get_client().post(f"/v1/models/{model_id}/unload", json=payload)
        response.raise_for_status()
        return response.json()

    async def download_model(
        self,
        model_id: str,
        url: str | None = None,
        repo: str | None = None,
        filename: str | None = None,
        token: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model_id": model_id,
            "url": url,
            "repo": repo,
            "filename": filename,
            "token": token,
            "overwrite": overwrite,
        }
        response = await self._get_client().post("/v1/models/download", json=payload, timeout=300.0)
        response.raise_for_status()
        return response.json()

    async def delete_model(self, model_id: str, delete_file: bool = False) -> dict[str, Any]:
        response = await self._get_client().delete(
            f"/v1/models/{model_id}", params={"delete_file": str(delete_file).lower()}
        )
        response.raise_for_status()
        return response.json()

    async def scan_models(self) -> dict[str, Any]:
        response = await self._get_client().post("/v1/models/scan")
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Providers
    # ------------------------------------------------------------------
    async def list_providers(self) -> list[dict[str, Any]]:
        response = await self._get_client().get("/v1/providers")
        response.raise_for_status()
        return response.json()

    async def get_provider(self, provider_name: str) -> dict[str, Any]:
        response = await self._get_client().get(f"/v1/providers/{provider_name}")
        response.raise_for_status()
        return response.json()

    async def provider_health(self, provider_name: str) -> dict[str, Any]:
        response = await self._get_client().get(f"/v1/providers/{provider_name}/health")
        response.raise_for_status()
        return response.json()

    async def provider_models(self, provider_name: str) -> dict[str, Any]:
        response = await self._get_client().get(f"/v1/providers/{provider_name}/models")
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------
    async def create_session(
        self,
        provider: str | None = None,
        model: str | None = None,
        role: str | None = None,
        system_prompt: str = "",
    ) -> dict[str, Any]:
        payload: dict[str, str | None] = {
            "provider": provider,
            "model": model,
            "role": role,
            "system_prompt": system_prompt,
        }
        response = await self._get_client().post("/v1/sessions", json=payload)
        response.raise_for_status()
        return response.json()

    async def list_sessions(self) -> dict[str, list[dict[str, Any]]]:
        response = await self._get_client().get("/v1/sessions")
        response.raise_for_status()
        return response.json()

    async def get_session(self, session_id: str) -> dict[str, Any]:
        response = await self._get_client().get(f"/v1/sessions/{session_id}")
        response.raise_for_status()
        return response.json()

    async def delete_session(self, session_id: str) -> dict[str, Any]:
        response = await self._get_client().delete(f"/v1/sessions/{session_id}")
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Network
    # ------------------------------------------------------------------
    async def network_status(self) -> dict[str, Any]:
        response = await self._get_client().get("/v1/network/status")
        response.raise_for_status()
        return response.json()

    async def scan_wifi(self, iface: str | None = None) -> list[dict[str, Any]]:
        params = {"iface": iface} if iface else {}
        response = await self._get_client().get("/v1/network/wifi/scan", params=params)
        response.raise_for_status()
        return response.json()

    async def connect_wifi(
        self, ssid: str, password: str | None = None, iface: str | None = None
    ) -> dict[str, Any]:
        payload = {"ssid": ssid, "password": password, "iface": iface}
        response = await self._get_client().post("/v1/network/wifi/connect", json=payload)
        response.raise_for_status()
        return response.json()

    async def disconnect_wifi(self, iface: str | None = None) -> dict[str, Any]:
        params = {"iface": iface} if iface else {}
        response = await self._get_client().post("/v1/network/wifi/disconnect", params=params)
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Voice
    # ------------------------------------------------------------------
    async def voice_status(self) -> dict[str, Any]:
        response = await self._get_client().get("/v1/voice/status")
        response.raise_for_status()
        return response.json()

    async def voice_devices(self) -> dict[str, Any]:
        response = await self._get_client().get("/v1/voice/devices")
        response.raise_for_status()
        return response.json()

    async def speak_text(self, text: str) -> dict[str, Any]:
        response = await self._get_client().post("/v1/voice/speak", json={"text": text})
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Memory
    # ------------------------------------------------------------------
    async def list_memories(self) -> dict[str, Any]:
        response = await self._get_client().get("/v1/memory/list")
        response.raise_for_status()
        return response.json()

    async def recall_memories(self, query: str, top_k: int = 10) -> dict[str, Any]:
        payload = {"query": query, "top_k": top_k}
        response = await self._get_client().post("/v1/memory/recall", json=payload)
        response.raise_for_status()
        return response.json()

    async def remember_memory(
        self, text: str, category: str = "general", source: str = "user"
    ) -> dict[str, Any]:
        payload = {"text": text, "category": category, "source": source}
        response = await self._get_client().post("/v1/memory/remember", json=payload)
        response.raise_for_status()
        return response.json()

    async def delete_memory(self, memory_id: str) -> dict[str, Any]:
        response = await self._get_client().delete(f"/v1/memory/{memory_id}")
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Plugins
    # ------------------------------------------------------------------
    async def list_plugins(self) -> dict[str, Any]:
        response = await self._get_client().get("/v1/plugins")
        response.raise_for_status()
        return response.json()

    async def enable_plugin(self, plugin_name: str) -> dict[str, Any]:
        response = await self._get_client().post(f"/v1/plugins/{plugin_name}/enable")
        response.raise_for_status()
        return response.json()

    async def disable_plugin(self, plugin_name: str) -> dict[str, Any]:
        response = await self._get_client().post(f"/v1/plugins/{plugin_name}/disable")
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # OpenAI compatible
    # ------------------------------------------------------------------
    async def openai_chat_completions(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        top_p: float = 0.95,
        stream: bool = False,
    ) -> Any:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": stream,
        }
        if stream:
            async with self._get_client().stream(
                "POST", "/v1/openai/chat/completions", json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        import json
                        yield json.loads(data)
        else:
            response = await self._get_client().post("/v1/openai/chat/completions", json=payload)
            response.raise_for_status()
            yield response.json()

    async def openai_list_models(self) -> dict[str, Any]:
        response = await self._get_client().get("/v1/openai/models")
        response.raise_for_status()
        return response.json()


def create_sdk(base_url: str = "http://localhost:8000", api_key: str | None = None) -> AtlasSDK:
    """Create an Atlas SDK instance."""
    return AtlasSDK(base_url=base_url, api_key=api_key)
