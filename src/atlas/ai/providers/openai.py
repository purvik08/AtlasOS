"""OpenAI provider via OpenAI-compatible API."""

from __future__ import annotations

from typing import Any

from atlas.ai.providers.base import ProviderRole
from atlas.ai.providers.openai_base import OpenAICompatibleProvider
from atlas.ai.providers.config import ProviderConfig


class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI provider using OpenAI-compatible API."""

    name = "openai"
    role = ProviderRole.CLOUD
    description = "OpenAI via OpenAI-compatible API"

    def __init__(self, config: ProviderConfig | None = None, **kwargs: Any) -> None:
        if config is None:
            from atlas.ai.providers.defaults import PROVIDER_DEFAULTS
            config = ProviderConfig(
                name=self.name,
                **PROVIDER_DEFAULTS[self.name],
                **kwargs,
            )
        super().__init__(config)