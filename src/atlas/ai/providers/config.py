"""Provider configuration dataclass."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ProviderConfig:
    """Per-provider configuration with extensible options."""

    name: str
    api_key: str = ""
    base_url: str = ""
    timeout_seconds: float = 60.0
    default_model: str = ""
    # Provider-specific extensions
    extra_headers: dict[str, str] = field(default_factory=dict)
    extra_params: dict[str, Any] = field(default_factory=dict)
    # Model routing hints
    preferred_models: list[str] = field(default_factory=list)
    fallback_models: list[str] = field(default_factory=list)
    # Capabilities
    supports_streaming: bool = True
    supports_functions: bool = False
    supports_vision: bool = False
    max_context_tokens: int = 4096