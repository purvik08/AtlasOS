"""Alibaba Qwen cloud provider implementation.

Uses :class:`~atlas.ai.providers.openai_base.OpenAICompatibleProvider` targeting
the DashScope OpenAI-compatible API at ``https://dashscope.aliyuncs.com/compatible-mode/v1``.
"""

from __future__ import annotations

import logging

from atlas.ai.providers.openai_base import OpenAICompatibleProvider

logger = logging.getLogger(__name__)

_QWEN_MODELS = [
    ("qwen-turbo", "Qwen Turbo", "Fast, cost-efficient Qwen model."),
    ("qwen-plus", "Qwen Plus", "Balanced capability and speed."),
    ("qwen-max", "Qwen Max", "Highest capability Qwen model."),
    ("qwen2.5-72b-instruct", "Qwen 2.5 72B Instruct", "Open-weight flagship model."),
    ("qwen2.5-7b-instruct", "Qwen 2.5 7B Instruct", "Efficient 7B open-weight model."),
]


class QwenProvider(OpenAICompatibleProvider):
    """Alibaba Qwen cloud provider targeting DashScope compatible API."""

    def __init__(self, api_key: str = "", timeout_seconds: float = 60.0) -> None:
        super().__init__(
            provider_name="qwen",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key=api_key,
            default_models=_QWEN_MODELS,
            timeout_seconds=timeout_seconds,
        )

    @property
    def description(self) -> str:
        return "Alibaba Qwen cloud inference (qwen-turbo, qwen-plus, qwen-max, ...)."
