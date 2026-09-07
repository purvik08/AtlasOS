"""In-memory prompt response cache manager for Atlas OS.

Avoids redundant LLM or cloud API calls by caching responses keyed by SHA-256
hashes of ``(model_id, formatted_messages, generation_kwargs)``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

from atlas.ai.providers.base import ChatResponse

logger = logging.getLogger(__name__)


class CacheManager:
    """In-memory response cache with TTL and max entries.

    Parameters
    ----------
    enabled:
        Whether caching is active.
    ttl_seconds:
        Time-To-Live in seconds for cached responses.
    max_entries:
        Maximum number of responses to keep in memory.
    """

    def __init__(
        self,
        enabled: bool = True,
        ttl_seconds: int = 3600,
        max_entries: int = 1000,
    ) -> None:
        self.enabled = enabled
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._cache: dict[str, tuple[ChatResponse, float]] = {}
        logger.debug("CacheManager initialised (enabled=%s, ttl=%ds).", enabled, ttl_seconds)

    def _make_key(self, model_id: str, messages: list[Any], kwargs: dict[str, Any]) -> str:
        serialized_messages = []
        for m in messages:
            role_attr = getattr(m, "role", None)
            if role_attr is not None and hasattr(role_attr, "value"):
                role_str = role_attr.value
            else:
                role_str = str(role_attr) if role_attr is not None else ""
            serialized_messages.append({"role": role_str, "content": getattr(m, "content", "")})
        key_data = {
            "model_id": model_id,
            "messages": serialized_messages,
            "kwargs": {k: str(v) for k, v in sorted(kwargs.items())},
        }
        raw_bytes = json.dumps(key_data, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw_bytes).hexdigest()

    def get(
        self, model_id: str, messages: list[Any], kwargs: dict[str, Any]
    ) -> ChatResponse | None:
        if not self.enabled:
            return None

        key = self._make_key(model_id, messages, kwargs)
        entry = self._cache.get(key)
        if entry is None:
            return None

        response, timestamp = entry
        if time.monotonic() - timestamp > self.ttl_seconds:
            # Expired
            del self._cache[key]
            return None

        logger.debug("CacheManager HIT for model '%s' (key=%s...).", model_id, key[:8])
        return response

    def set(
        self,
        model_id: str,
        messages: list[Any],
        kwargs: dict[str, Any],
        response: ChatResponse,
    ) -> None:
        if not self.enabled:
            return

        if len(self._cache) >= self.max_entries:
            # Evict oldest entry
            oldest_key = min(self._cache, key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]

        key = self._make_key(model_id, messages, kwargs)
        self._cache[key] = (response, time.monotonic())
        logger.debug("CacheManager STORED entry for model '%s' (key=%s...).", model_id, key[:8])

    def clear(self) -> None:
        self._cache.clear()
        logger.debug("CacheManager cleared.")

    def __len__(self) -> int:
        return len(self._cache)
