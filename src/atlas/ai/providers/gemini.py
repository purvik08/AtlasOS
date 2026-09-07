"""Google Gemini cloud provider implementation using httpx.

Targets the official Google Generative Language REST API at
``https://generativelanguage.googleapis.com/v1beta``.
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

_GEMINI_MODELS = [
    ("gemini-1.5-flash", "Gemini 1.5 Flash", "Fast, efficient multimodal model."),
    ("gemini-1.5-pro", "Gemini 1.5 Pro", "High-capability multimodal model."),
    ("gemini-2.0-flash", "Gemini 2.0 Flash", "Next-gen fast model."),
]


class GeminiProvider(AIProvider):
    """Google Gemini cloud provider using direct REST API requests."""

    def __init__(self, api_key: str = "", timeout_seconds: float = 60.0) -> None:
        self._api_key = api_key
        self._timeout = timeout_seconds
        self._loaded_models: set[str] = set()
        logger.debug("GeminiProvider initialised. Key %s.", "SET" if api_key else "NOT SET")

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def role(self) -> ProviderRole:
        return ProviderRole.CLOUD

    @property
    def description(self) -> str:
        return "Google Gemini cloud inference (gemini-1.5-flash, gemini-1.5-pro, ...)."

    async def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                model_id=mid,
                display_name=name,
                provider_name=self.name,
                loaded=mid in self._loaded_models,
                description=desc,
            )
            for mid, name, desc in _GEMINI_MODELS
        ]

    async def load_model(self, model_id: str) -> None:
        valid_ids = {m[0] for m in _GEMINI_MODELS}
        if model_id not in valid_ids:
            known = sorted(valid_ids)
            raise ValueError(
                f"Unknown Gemini model: {model_id!r}. Known models: {known}."
            )
        raise ValueError(
            f"Cloud model '{model_id}' (provider '{self.name}') "
            f"does not require loading. Cloud models execute remotely "
            f"via API. Configure your API key "
            f"(ATLAS_AI__GEMINI_API_KEY) and check status using "
            f"'atlas provider health {self.name}'."
        )

    async def unload_model(self, model_id: str) -> None:
        # No local memory lifecycle for cloud providers; unload is a safe no-op.
        self._loaded_models.discard(model_id)
        logger.debug("%s: unload_model('%s') is a no-op for cloud providers.", self.name, model_id)

    def _format_contents(self, messages: list[Message]) -> list[dict[str, Any]]:
        contents = []
        for m in messages:
            role = "user" if m.role in (MessageRole.USER, MessageRole.SYSTEM) else "model"
            contents.append({
                "role": role,
                "parts": [{"text": m.content}]
            })
        return contents

    async def chat(
        self,
        messages: list[Message],
        model_id: str,
        **kwargs: Any,
    ) -> ChatResponse:
        start = time.monotonic()

        if not self._api_key:
            user_text = messages[-1].content if messages else ""
            stub_reply = (
                f"[Gemini API Key Not Configured] "
                f"Please set ATLAS_AI__GEMINI_API_KEY to enable live inference. "
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

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_id}:generateContent?key={self._api_key}"
        )
        payload: dict[str, Any] = {
            "contents": self._format_contents(messages)
        }
        gen_config: dict[str, Any] = {}
        if "temperature" in kwargs:
            gen_config["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            gen_config["maxOutputTokens"] = kwargs["max_tokens"]
        if "top_p" in kwargs:
            gen_config["topP"] = kwargs["top_p"]
        if gen_config:
            payload["generationConfig"] = gen_config

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        latency = (time.monotonic() - start) * 1000
        content_text = ""
        try:
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                content_text = "".join(p.get("text", "") for p in parts)
        except Exception as exc:
            logger.warning("Gemini parsing error: %s", exc)

        return ChatResponse(
            message=Message(role=MessageRole.ASSISTANT, content=content_text),
            provider_name=self.name,
            model_id=model_id,
            prompt_tokens=sum(len(m.content.split()) for m in messages),
            completion_tokens=len(content_text.split()),
            latency_ms=latency,
        )

    async def stream_chat(
        self,
        messages: list[Message],
        model_id: str,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        if not self._api_key:
            res = await self.chat(messages, model_id, **kwargs)
            for word in res.message.content.split():
                yield word + " "
            return

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_id}:streamGenerateContent?key={self._api_key}&alt=sse"
        )
        payload = {"contents": self._format_contents(messages)}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if line.startswith("data: "):
                        raw_data = line[6:]
                        try:
                            parsed = json.loads(raw_data)
                            candidates = parsed.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                text = "".join(p.get("text", "") for p in parts)
                                if text:
                                    yield text
                        except json.JSONDecodeError:
                            continue

    async def health(self) -> ProviderHealth:
        if not self._api_key:
            return ProviderHealth(
                provider_name=self.name,
                status=ProviderStatus.UNHEALTHY,
                loaded_models=list(self._loaded_models),
                message="No API key configured. Set ATLAS_AI__GEMINI_API_KEY.",
            )
        return ProviderHealth(
            provider_name=self.name,
            status=ProviderStatus.HEALTHY,
            loaded_models=list(self._loaded_models),
            message="API key present; ready for inference.",
        )
