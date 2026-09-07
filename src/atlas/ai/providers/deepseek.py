"""DeepSeek cloud provider implementation.

Uses :class:`~atlas.ai.providers.openai_base.OpenAICompatibleProvider` targeting
the official DeepSeek API at ``https://api.deepseek.com``.
"""

from __future__ import annotations

import logging

from atlas.ai.providers.openai_base import OpenAICompatibleProvider

logger = logging.getLogger(__name__)

_DEEPSEEK_MODELS = [
    ("deepseek-chat", "DeepSeek Chat", "General-purpose conversational model."),
    ("deepseek-coder", "DeepSeek Coder", "Code generation and understanding."),
    ("deepseek-reasoner", "DeepSeek Reasoner", "Chain-of-thought reasoning model."),
]


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek cloud inference provider targeting api.deepseek.com."""

    def __init__(self, api_key: str = "", timeout_seconds: float = 60.0) -> None:
        super().__init__(
            provider_name="deepseek",
            base_url="https://api.deepseek.com",
            api_key=api_key,
            default_models=_DEEPSEEK_MODELS,
            timeout_seconds=timeout_seconds,
        )

    @property
    def description(self) -> str:
        return "DeepSeek cloud inference (deepseek-chat, deepseek-coder, deepseek-reasoner)."
