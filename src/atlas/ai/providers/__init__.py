"""Atlas OS AI providers sub-package.

Exposes all concrete :class:`~atlas.ai.providers.base.AIProvider` implementations
and the shared data models so callers can import from a single location::

    from atlas.ai.providers import AIProvider, LlamaCppProvider, GeminiProvider
"""

from atlas.ai.providers.base import (
    AIProvider,
    ChatResponse,
    Message,
    MessageRole,
    ModelInfo,
    ProviderHealth,
    ProviderInfo,
    ProviderRole,
    ProviderStatus,
)
from atlas.ai.providers.deepseek import DeepSeekProvider
from atlas.ai.providers.gemini import GeminiProvider
from atlas.ai.providers.kimi import KimiProvider
from atlas.ai.providers.llama_cpp import LlamaCppProvider
from atlas.ai.providers.qwen import QwenProvider

__all__ = [
    # Abstract interface
    "AIProvider",
    # Data models
    "ChatResponse",
    "Message",
    "MessageRole",
    "ModelInfo",
    "ProviderHealth",
    "ProviderInfo",
    "ProviderRole",
    "ProviderStatus",
    # Concrete providers
    "DeepSeekProvider",
    "GeminiProvider",
    "KimiProvider",
    "LlamaCppProvider",
    "QwenProvider",
]
