"""Inference execution engine for Atlas OS.

The :class:`InferenceEngine` orchestrates inference calls by applying
parameter sanitization, response caching, retry policies, timeouts, and
exception normalization across provider routing.
"""

from __future__ import annotations

import asyncio
import builtins
import logging
from collections.abc import AsyncIterator
from typing import Any

from atlas.ai.cache import CacheManager
from atlas.ai.prompt import PromptManager
from atlas.ai.providers.base import ChatResponse, Message
from atlas.ai.router import AIRouter

logger = logging.getLogger(__name__)


class InferenceError(RuntimeError):
    """Base exception for inference engine failures."""


class TimeoutError(InferenceError):
    """Raised when an inference call times out."""


class RateLimitError(InferenceError):
    """Raised when a cloud provider returns a rate limit error."""


class InferenceEngine:
    """Orchestrates inference requests through the provider router.

    Parameters
    ----------
    router:
        The provider selection router.
    cache_manager:
        Response cache manager.
    prompt_manager:
        Prompt template manager.
    max_retries:
        Maximum retries for transient errors.
    timeout_seconds:
        Timeout cap in seconds for inference requests.
    """

    def __init__(
        self,
        router: AIRouter,
        cache_manager: CacheManager | None = None,
        prompt_manager: PromptManager | None = None,
        max_retries: int = 3,
        timeout_seconds: float = 60.0,
    ) -> None:
        self._router = router
        self._cache = cache_manager or CacheManager(enabled=False)
        self._prompt = prompt_manager or PromptManager()
        self._max_retries = max_retries
        self._timeout = timeout_seconds
        logger.debug("InferenceEngine initialised.")

    def sanitize_kwargs(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Validate and sanitize generation parameters."""
        sanitized = dict(kwargs)
        if "temperature" in sanitized:
            sanitized["temperature"] = max(0.0, min(2.0, float(sanitized["temperature"])))
        if "top_p" in sanitized:
            sanitized["top_p"] = max(0.0, min(1.0, float(sanitized["top_p"])))
        if "max_tokens" in sanitized:
            sanitized["max_tokens"] = max(1, int(sanitized["max_tokens"]))
        return sanitized

    async def execute_chat(
        self,
        messages: list[Message],
        model_id: str,
        provider_name: str | None = None,
        role: Any = None,
        system_prompt: str = "",
        **kwargs: Any,
    ) -> ChatResponse:
        """Execute a chat request through the full inference pipeline."""
        sanitized_kwargs = self.sanitize_kwargs(kwargs)
        formatted_messages = self._prompt.format_messages(messages, system_prompt)

        # Check cache
        cached = self._cache.get(model_id, formatted_messages, sanitized_kwargs)
        if cached is not None:
            return cached

        # Route provider
        provider = self._router.select_with_fallback(
            provider_name=provider_name, role=role
        )

        attempt = 0
        last_exception: Exception | None = None

        while attempt <= self._max_retries:
            try:
                # Execute with timeout
                response = await asyncio.wait_for(
                    provider.chat(formatted_messages, model_id=model_id, **sanitized_kwargs),
                    timeout=self._timeout,
                )
                # Store in cache
                self._cache.set(model_id, formatted_messages, sanitized_kwargs, response)
                return response
            except builtins.TimeoutError:
                logger.warning(
                    "InferenceEngine: attempt %d/%d timed out for provider '%s'.",
                    attempt + 1, self._max_retries + 1, provider.name
                )
                last_exception = TimeoutError(f"Inference timed out after {self._timeout}s.")
            except Exception as exc:
                err_msg = str(exc).lower()
                if "429" in err_msg or "rate limit" in err_msg:
                    last_exception = RateLimitError(str(exc))
                else:
                    last_exception = InferenceError(str(exc))

                logger.warning(
                    "InferenceEngine: attempt %d/%d failed for provider '%s': %s",
                    attempt + 1, self._max_retries + 1, provider.name, exc
                )

            attempt += 1
            if attempt <= self._max_retries:
                await asyncio.sleep(0.2 * (2 ** (attempt - 1)))  # exponential backoff

        raise last_exception or InferenceError("Inference failed after retries.")

    async def execute_stream_chat(
        self,
        messages: list[Message],
        model_id: str,
        provider_name: str | None = None,
        role: Any = None,
        system_prompt: str = "",
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream chat tokens through provider routing."""
        sanitized_kwargs = self.sanitize_kwargs(kwargs)
        formatted_messages = self._prompt.format_messages(messages, system_prompt)

        provider = self._router.select_with_fallback(
            provider_name=provider_name, role=role
        )

        async for chunk in provider.stream_chat(
            formatted_messages, model_id=model_id, **sanitized_kwargs
        ):
            yield chunk
