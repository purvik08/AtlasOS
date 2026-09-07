"""Abstract base class for OpenAI-compatible cloud REST providers.

Provides a unified, production-ready REST client using ``httpx.AsyncClient``
for providers that expose the standard ``/v1/chat/completions`` format (DeepSeek,
Qwen, Kimi, Ollama REST, etc.).

Features
--------
* Full async non-blocking HTTP requests via ``httpx``.
* Server-Sent Events (SSE) parser for streaming token deltas.
* Proper HTTP error mapping (401 Unauthorized, 429 Rate Limit, 500+ Server Errors).
* Custom headers (e.g. Bearer token authorization).
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from atlas.ai.providers.base import (
    AIProvider,
    ChatResponse,
    Message,
    MessageRole,
    ModelInfo,
    ProviderHealth,
    ProviderRole,
    ProviderStatus,
)

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(AIProvider):
    """Base class for OpenAI-compatible chat completion APIs."""

    def __init__(
        self,
        provider_name: str,
        base_url: str,
        api_key: str = "",
        default_models: list[tuple[str, str, str]] | None = None,
        timeout_seconds: float = 60.0,
    ) -> None:
        self._provider_name = provider_name
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout_seconds
        self._default_models = default_models or []
        self._loaded_models: set[str] = set()

    @property
    def name(self) -> str:
        return self._provider_name

    @property
    def role(self) -> ProviderRole:
        return ProviderRole.CLOUD

    async def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                model_id=mid,
                display_name=name,
                provider_name=self.name,
                loaded=mid in self._loaded_models,
                description=desc,
            )
            for mid, name, desc in self._default_models
        ]

    async def load_model(self, model_id: str) -> None:
        # Cloud models are not loaded into local memory; they execute remotely.
        # Provide a clear, actionable error so callers (CLI / manager) can
        # guide the user toward configuring an API key instead.
        valid_ids = {m[0] for m in self._default_models}
        if valid_ids and model_id not in valid_ids:
            raise ValueError(
                f"Unknown {self.name} model: {model_id!r}. "
                f"Known models: {sorted(valid_ids)}."
            )
        env_var = f"ATLAS_AI__{self.name.upper()}_API_KEY"
        raise ValueError(
            f"Cloud model '{model_id}' (provider '{self.name}') does not require loading. "
            f"Cloud models execute remotely via API. "
            f"Configure your API key ({env_var}) and check status using "
            f"'atlas provider health {self.name}'."
        )

    async def unload_model(self, model_id: str) -> None:
        # No local memory lifecycle exists for cloud providers; unload is a
        # no-op that mirrors the new semantics introduced for local/cloud
        # separation rather than raising, so callers can invoke it safely
        # after a previously rejected load_model.
        self._loaded_models.discard(model_id)
        logger.debug("%s: unload_model('%s') is a no-op for cloud providers.", self.name, model_id)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _format_messages(self, messages: list[Message]) -> list[dict[str, str]]:
        return [{"role": m.role.value, "content": m.content} for m in messages]

    async def chat(
        self,
        messages: list[Message],
        model_id: str,
        **kwargs: Any,
    ) -> ChatResponse:
        """Perform non-streaming POST request to /chat/completions."""
        start = time.monotonic()

        if not self._api_key:
            # When API key is omitted, log warning and return helpful message
            user_text = messages[-1].content if messages else ""
            stub_reply = (
                f"[{self.name} API Key Not Configured] "
                f"Please set ATLAS_AI__{self.name.upper()}_API_KEY to enable live inference. "
                f"Received: '{user_text}'."
            )
            return ChatResponse(
                message=Message(role=MessageRole.ASSISTANT, content=stub_reply),
                provider_name=self.name,
                model_id=model_id,
                prompt_tokens=sum(len(m.content.split()) for m in messages),
                completion_tokens=len(stub_reply.split()),
                latency_ms=(time.monotonic() - start) * 1000,
            )

        endpoint = f"{self._base_url}/chat/completions"
        payload = {
            "model": model_id,
            "messages": self._format_messages(messages),
            "stream": False,
        }
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            payload["max_tokens"] = kwargs["max_tokens"]
        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                endpoint,
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        latency = (time.monotonic() - start) * 1000
        choice = data["choices"][0]["message"]
        usage = data.get("usage", {})

        return ChatResponse(
            message=Message(
                role=MessageRole(choice.get("role", "assistant")),
                content=choice.get("content", ""),
            ),
            provider_name=self.name,
            model_id=model_id,
            prompt_tokens=usage.get("prompt_tokens", -1),
            completion_tokens=usage.get("completion_tokens", -1),
            latency_ms=latency,
        )

    async def stream_chat(
        self,
        messages: list[Message],
        model_id: str,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Perform streaming POST request to /chat/completions via SSE."""
        if not self._api_key:
            res = await self.chat(messages, model_id, **kwargs)
            for word in res.message.content.split():
                yield word + " "
            return

        endpoint = f"{self._base_url}/chat/completions"
        payload = {
            "model": model_id,
            "messages": self._format_messages(messages),
            "stream": True,
        }
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            payload["max_tokens"] = kwargs["max_tokens"]

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                "POST",
                endpoint,
                headers=self._headers(),
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or line == "data: [DONE]":
                        continue
                    if line.startswith("data: "):
                        raw_data = line[6:]
                        try:
                            parsed = json.loads(raw_data)
                            delta = parsed["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue

    async def health(self) -> ProviderHealth:
        if not self._api_key:
            return ProviderHealth(
                provider_name=self.name,
                status=ProviderStatus.UNHEALTHY,
                loaded_models=list(self._loaded_models),
                message=f"No API key configured. Set ATLAS_AI__{self.name.upper()}_API_KEY.",
            )
        return ProviderHealth(
            provider_name=self.name,
            status=ProviderStatus.HEALTHY,
            loaded_models=list(self._loaded_models),
            message="API key configured; ready for inference.",
        )
