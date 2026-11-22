"""Anthropic provider via Messages API."""

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


class AnthropicProvider(AIProvider):
    """Anthropic provider using Messages API."""

    name = "anthropic"
    role = ProviderRole.CLOUD
    description = "Anthropic Claude via Messages API"

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {
                "x-api-key": self._config.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            headers.update(self._config.extra_headers)
            self._client = httpx.AsyncClient(
                base_url=self._config.base_url.rstrip("/"),
                headers=headers,
                timeout=self._config.timeout_seconds,
            )
        return self._client

    def _convert_messages(
        self,
        messages: list[ChatMessage],
        system_prompt: str = "",
    ) -> tuple[list[dict[str, Any]], str]:
        """Convert internal messages to Anthropic format."""
        anthropic_messages = []

        # Handle system prompt separately for Anthropic
        if system_prompt:
            # Anthropic uses a separate system parameter
            pass

        for msg in messages:
            if msg.role == "system" and not system_prompt:
                system_prompt = msg.content
            else:
                anthropic_messages.append({"role": msg.role, "content": msg.content})

        return anthropic_messages, system_prompt

    async def list_models(self) -> list[ModelInfo]:
        """List available models from the API."""
        if not self._config.api_key:
            return [ModelInfo(
                model_id=self._config.default_model or "unknown",
                display_name=self._config.default_model or "unknown",
                provider_name=self.name,
                loaded=False,
                description="Configure API key to list models",
            )]

        # Anthropic doesn't have a models endpoint, return configured models
        models = []
        for model_id in self._config.preferred_models:
            models.append(ModelInfo(
                model_id=model_id,
                display_name=model_id,
                provider_name=self.name,
                loaded=False,
                description="Anthropic Claude model",
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

        anthropic_messages, system = self._convert_messages(messages, system_prompt)

        payload = {
            "model": model_id or self._config.default_model,
            "messages": anthropic_messages,
            "max_tokens": kwargs.get("max_tokens", 1024),
            "temperature": kwargs.get("temperature", 0.7),
            **self._config.extra_params,
            **kwargs,
        }
        if system:
            payload["system"] = system

        response = await client.post("/v1/messages", json=payload)
        response.raise_for_status()
        data = response.json()
        latency = (time.time() - start) * 1000

        content = data["content"][0]["text"] if data["content"] else ""
        usage = data.get("usage", {})

        return ChatResponse(
            message=ChatMessage(role="assistant", content=content),
            model_id=model_id or self._config.default_model,
            provider_name=self.name,
            prompt_tokens=usage.get("input_tokens", 0),
            completion_tokens=usage.get("output_tokens", 0),
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

        anthropic_messages, system = self._convert_messages(messages, system_prompt)

        payload = {
            "model": model_id or self._config.default_model,
            "messages": anthropic_messages,
            "max_tokens": kwargs.get("max_tokens", 1024),
            "temperature": kwargs.get("temperature", 0.7),
            "stream": True,
            **self._config.extra_params,
            **kwargs,
        }
        if system:
            payload["system"] = system

        async with client.stream("POST", "/v1/messages", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        import json
                        data = json.loads(data_str)
                        if data.get("type") == "content_block_delta":
                            delta = data.get("delta", {})
                            if delta.get("type") == "text_delta":
                                yield delta.get("text", "")
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
            # Anthropic doesn't have a health endpoint, try a simple request
            response = await client.post(
                "/v1/messages",
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
        """Cloud models don't need local loading."""
        raise NotImplementedError(
            f"{self.name} is a cloud provider - models don't require local loading"
        )

    async def unload_model(self, model_id: str) -> None:
        """Cloud models don't need local unloading."""
        raise NotImplementedError(
            f"{self.name} is a cloud provider - models don't require local unloading"
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None