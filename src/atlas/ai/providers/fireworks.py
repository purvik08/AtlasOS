"""Fireworks AI provider via OpenAI-compatible API."""

from __future__ import annotations

from typing import Any

from atlas.ai.providers.base import ProviderRole
from atlas.ai.providers.openai_base import OpenAICompatibleProvider
from atlas.ai.providers.config import ProviderConfig


class FireworksProvider(OpenAICompatibleProvider):
    """Fireworks AI provider using OpenAI-compatible API."""

    name = "fireworks"
    role = ProviderRole.CLOUD
    description = "Fireworks AI via OpenAI-compatible API"

    def __init__(self, config: ProviderConfig | None = None, **kwargs: Any) -> None:
        if config is None:
            from atlas.ai.providers.defaults import PROVIDER_DEFAULTS
            config = ProviderConfig(
                name=self.name,
                **PROVIDER_DEFAULTS[self.name],
                **kwargs,
            )
        super().__init__(config)