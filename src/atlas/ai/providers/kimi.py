"""Kimi / Moonshot AI cloud provider implementation.

Uses :class:`~atlas.ai.providers.openai_base.OpenAICompatibleProvider` targeting
the Moonshot AI API at ``https://api.moonshot.cn/v1``.
"""

from __future__ import annotations

import logging

from atlas.ai.providers.openai_base import OpenAICompatibleProvider

logger = logging.getLogger(__name__)

_KIMI_MODELS = [
    ("moonshot-v1-8k", "Kimi v1 8K", "8K context window model."),
    ("moonshot-v1-32k", "Kimi v1 32K", "32K context window model."),
    ("moonshot-v1-128k", "Kimi v1 128K", "128K long-context model."),
]


class KimiProvider(OpenAICompatibleProvider):
    """Kimi / Moonshot AI cloud provider targeting api.moonshot.cn."""

    def __init__(self, api_key: str = "", timeout_seconds: float = 60.0) -> None:
        super().__init__(
            provider_name="kimi",
            base_url="https://api.moonshot.cn/v1",
            api_key=api_key,
            default_models=_KIMI_MODELS,
            timeout_seconds=timeout_seconds,
        )

    @property
    def description(self) -> str:
        return "Kimi / Moonshot AI cloud inference (moonshot-v1-8k/32k/128k)."
