"""Google Vertex AI provider."""

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


class VertexAIProvider(AIProvider):
    """Google Vertex AI provider."""

    name = "vertex_ai"
    role = ProviderRole.CLOUD
    description = "Google Vertex AI (Gemini)"

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._client: httpx.AsyncClient | None = None
        self._project_id = config.extra_params.get("project_id", "")
        self._location = config.extra_params.get("location", "us-central1")

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            # Vertex AI uses OAuth2, but for simplicity we'll use API key if provided
            headers = {"Content-Type": "application/json"}
            if self._config.api_key:
                headers["Authorization"] = f"Bearer {self._config.api_key}"
            headers.update(self._config.extra_headers)
            self._client = httpx.AsyncClient(
                base_url=f"https://{self._location}-aiplatform.googleapis.com/v1/projects/{self._project_id}/locations/{self._location}",
                headers=headers,
                timeout=self._config.timeout_seconds,
            )
        return self._client

    async def list_models(self) -> list[ModelInfo]:
        """List available models."""
        if not self._config.api_key and not (self._project_id and self._location):
            return [ModelInfo(
                model_id=self._config.default_model or "unknown",
                display_name=self._config.default_model or "unknown",
                provider_name=self.name,
                loaded=False,
                description="Configure credentials to list models",
            )]

        models = []
        for model_id in self._config.preferred_models:
            models.append(ModelInfo(
                model_id=model_id,
                display_name=model_id,
                provider_name=self.name,
                loaded=False,
                description="Vertex AI Gemini model",
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

        # Convert to Vertex AI format
        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": system_prompt}]})
            contents.append({"role": "model", "parts": [{"text": "OK"}]})

        for msg in messages:
            role = "user" if msg.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg.content}]})

        model = model_id or self._config.default_model
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.7),
                "maxOutputTokens": kwargs.get("max_tokens", 1024),
                "topP": kwargs.get("top_p", 0.95),
            },
        }
        payload.update(self._config.extra_params)

        url = f"/publishers/google/models/{model}:generateContent"
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        latency = (time.time() - start) * 1000

        content = ""
        if data.get("candidates"):
            candidate = data["candidates"][0]
            if candidate.get("content", {}).get("parts"):
                content = candidate["content"]["parts"][0].get("text", "")

        usage = data.get("usageMetadata", {})

        return ChatResponse(
            message=ChatMessage(role="assistant", content=content),
            model_id=model,
            provider_name=self.name,
            prompt_tokens=usage.get("promptTokenCount", 0),
            completion_tokens=usage.get("candidatesTokenCount", 0),
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

        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": system_prompt}]})
            contents.append({"role": "model", "parts": [{"text": "OK"}]})

        for msg in messages:
            role = "user" if msg.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg.content}]})

        model = model_id or self._config.default_model
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.7),
                "maxOutputTokens": kwargs.get("max_tokens", 1024),
                "topP": kwargs.get("top_p", 0.95),
            },
        }
        payload.update(self._config.extra_params)

        url = f"/publishers/google/models/{model}:streamGenerateContent"
        async with client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip():
                    try:
                        import json
                        data = json.loads(line)
                        if data.get("candidates"):
                            candidate = data["candidates"][0]
                            if candidate.get("content", {}).get("parts"):
                                yield candidate["content"]["parts"][0].get("text", "")
                    except Exception:
                        pass

    async def health(self) -> ProviderHealth:
        """Check provider health."""
        if not self._config.api_key and not (self._project_id and self._location):
            return ProviderHealth(
                provider_name=self.name,
                status=ProviderStatus.UNHEALTHY,
                loaded_models=[],
                message="Credentials not configured",
            )

        try:
            client = self._get_client()
            model = self._config.default_model
            response = await client.post(
                f"/publishers/google/models/{model}:generateContent",
                json={
                    "contents": [{"role": "user", "parts": [{"text": "ping"}]}],
                    "generationConfig": {"maxOutputTokens": 1},
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