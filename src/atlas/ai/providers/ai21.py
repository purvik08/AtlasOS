"""AI21 provider (native API)."""

from __future__ import annotations

import time
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from atlas.ai.providers.base import (
    AIProvider,
    ChatMessage,
    ChatResponse,
    ModelInfo,
    ProviderHealth,
    ProviderRole,
    ProviderStatus,
)
from atlas.ai.providers.config import ProviderConfig


class AI21Provider(AIProvider):
    """AI21 provider using native Chat API."""

    name = "ai21"
    role = ProviderRole.CLOUD
    description = "AI21 (Jamba)"

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {
                "Authorization": f"Bearer {self._config.api_key}",
                "Content-Type": "application/json",
            }
            headers.update(self._config.extra_headers)
            self._client = httpx.AsyncClient(
                base_url=self._config.base_url.rstrip("/"),
                headers=headers,
                timeout=self._config.timeout_seconds,
            )
        return self._client

    async def list_models(self) -> list[ModelInfo]:
        """List available models."""
        models = []
        for model_id in self._config.preferred_models:
            models.append(ModelInfo(
                model_id=model_id,
                display_name=model_id,
                provider_name=self.name,
                loaded=False,
                description="AI21 model",
            ))
        return models

    async def chat(
        self,
        messages: list[ChatMessage],
        model_id: str,
        system_prompt: str = "",
        **kwargs: Any,
    ) -> ChatResponse:
        """Non-streaming chat completion."""
        start = time.time()
        client = self._get_client()

        # Convert to AI21 format
        messages_ai21 = []
        if system_prompt:
            messages_ai21.append({"role": "system", "content": system_prompt})

        for msg in messages:
            messages_ai21.append({"role": msg.role, "content": msg.content})

        model = model_id or self._config.default_model
        payload = {
            "model": model,
            "messages": messages_ai21,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1024),
            "top_p": kwargs.get("top_p", 0.95),
        }
        payload.update(self._config.extra_params)

        response = await client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        latency = (time.time() - start) * 1000

        content = ""
        if data.get("choices"):
            content = data["choices"][0].get("message", {}).get("content", "")

        usage = data.get("usage", {})

        return ChatResponse(
            message=ChatMessage(role="assistant", content=content),
            model_id=model,
            provider_name=self.name,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            latency_ms=latency,
        )

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        model_id: str,
        system_prompt: str = "",
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Streaming chat completion."""
        client = self._get_client()

        messages_ai21 = []
        if system_prompt:
            messages_ai21.append({"role": "system", "content": system_prompt})

        for msg in messages:
            messages_ai21.append({"role": msg.role, "content": msg.content})

        model = model_id or self._config.default_model
        payload = {
            "model": model,
            "messages": messages_ai21,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1024),
            "top_p": kwargs.get("top_p", 0.95),
            "stream": True,
        }
        payload.update(self._config.extra_params)

        async with client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        import json
                        data = json.loads(data_str)
                        if data.get("choices"):
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                    except Exception:
                        pass

    async def health(self) -> ProviderHealth:
        """Check provider health."""
        if not self._config.api_key:
            return ProviderHealth(
                provider_name=self.name,
                status=ProviderStatus.UNHEALTHY,
                loaded_models=[],
                message="API key not configured",
            )

        try:
            client = self._get_client()
            response = await client.post(
                "/chat/completions",
                json={
                    "model": self._config.default_model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                },
            )
            if response.status_code == 200:
                return ProviderHealth(
                    provider_name=self.name,
                    status=ProviderStatus.HEALTHY,
                    loaded_models=[],
                    message="API accessible",
                )
            return ProviderHealth(
                provider_name=self.name,
                status=ProviderStatus.DEGRADED,
                loaded_models=[],
                message=f"API returned {response.status_code}",
            )
        except Exception as e:
            return ProviderHealth(
                provider_name=self.name,
                status=ProviderStatus.UNHEALTHY,
                loaded_models=[],
                message=str(e),
            )

    async def load_model(self, model_id: str) -> None:
        raise NotImplementedError(
            f"{self.name} is a cloud provider - models don't require local loading"
        )

    async def unload_model(self, model_id: str) -> None:
        raise NotImplementedError(
            f"{self.name} is a cloud provider - models don't require local unloading"
        )

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None