"""DeepSeek cloud provider stub.

Implements the full :class:`~atlas.ai.providers.base.AIProvider` interface for
the DeepSeek API (``deepseek-chat``, ``deepseek-coder``, ``deepseek-reasoner``).
HTTP calls to ``api.deepseek.com`` are **stubbed**.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from typing import Any

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

_DEEPSEEK_MODELS = [
    ("deepseek-chat", "DeepSeek Chat", "General-purpose conversational model."),
    ("deepseek-coder", "DeepSeek Coder", "Code generation and understanding."),
    ("deepseek-reasoner", "DeepSeek Reasoner", "Chain-of-thought reasoning model."),
]


class DeepSeekProvider(AIProvider):
    """DeepSeek cloud inference provider.

    Parameters
    ----------
    api_key:
        DeepSeek API key (``ATLAS_AI__DEEPSEEK_API_KEY``).
    """

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key
        self._loaded_models: set[str] = set()
        logger.debug(
            "DeepSeekProvider initialised. API key %s.",
            "present" if api_key else "NOT SET",
        )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:  # noqa: D102
        return "deepseek"

    @property
    def role(self) -> ProviderRole:  # noqa: D102
        return ProviderRole.CLOUD

    @property
    def description(self) -> str:  # noqa: D102
        return "DeepSeek cloud inference (deepseek-chat, deepseek-coder, deepseek-reasoner)."

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    async def list_models(self) -> list[ModelInfo]:  # noqa: D102
        return [
            ModelInfo(
                model_id=mid,
                display_name=name,
                provider_name=self.name,
                loaded=mid in self._loaded_models,
                description=desc,
            )
            for mid, name, desc in _DEEPSEEK_MODELS
        ]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def load_model(self, model_id: str) -> None:
        """Activate *model_id* for cloud requests."""
        valid_ids = {m[0] for m in _DEEPSEEK_MODELS}
        if model_id not in valid_ids:
            raise ValueError(f"Unknown DeepSeek model: {model_id!r}")
        self._loaded_models.add(model_id)
        logger.info("[STUB] DeepSeek: activated model '%s'.", model_id)

    async def unload_model(self, model_id: str) -> None:
        """De-register *model_id*."""
        self._loaded_models.discard(model_id)
        logger.info("[STUB] DeepSeek: deactivated model '%s'.", model_id)

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    async def chat(
        self,
        messages: list[Message],
        model_id: str,
        **kwargs: Any,
    ) -> ChatResponse:
        """Return a stubbed DeepSeek response."""
        if not self._api_key:
            logger.warning("DeepSeekProvider: no API key configured — returning stub.")

        start = time.monotonic()
        await asyncio.sleep(0)

        user_text = messages[-1].content if messages else ""
        stub_reply = (
            f"[DeepSeek STUB / {model_id}] You said: '{user_text}'. "
            "Set ATLAS_AI__DEEPSEEK_API_KEY and wire in httpx calls to go live."
        )
        latency = (time.monotonic() - start) * 1000

        return ChatResponse(
            message=Message(role=MessageRole.ASSISTANT, content=stub_reply),
            provider_name=self.name,
            model_id=model_id,
            prompt_tokens=sum(len(m.content.split()) for m in messages),
            completion_tokens=len(stub_reply.split()),
            latency_ms=latency,
        )

    async def stream_chat(  # type: ignore[override]
        self,
        messages: list[Message],
        model_id: str,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Yield stub tokens word by word."""
        response = await self.chat(messages, model_id, **kwargs)
        for word in response.message.content.split():
            await asyncio.sleep(0.005)
            yield word + " "

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    async def health(self) -> ProviderHealth:
        """Report healthy only when an API key is present."""
        if not self._api_key:
            return ProviderHealth(
                provider_name=self.name,
                status=ProviderStatus.UNHEALTHY,
                loaded_models=list(self._loaded_models),
                message="No API key configured. Set ATLAS_AI__DEEPSEEK_API_KEY.",
            )
        return ProviderHealth(
            provider_name=self.name,
            status=ProviderStatus.HEALTHY,
            loaded_models=list(self._loaded_models),
            message="API key present; ready for inference.",
        )
