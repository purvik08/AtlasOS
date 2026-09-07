"""Atlas OS AI providers sub-package.

Exposes all concrete :class:`~atlas.ai.providers.base.AIProvider` implementations,
the base classes, and shared data models.
"""

from atlas.ai.providers.base import (
    AIProvider,
    ChatResponse,
    Message,
    MessageRole,
    ModelInfo,
    ProviderCapabilities,
    ProviderHealth,
    ProviderInfo,
    ProviderRole,
    ProviderStatus,
)
from atlas.ai.providers.deepseek import DeepSeekProvider
from atlas.ai.providers.gemini import GeminiProvider
from atlas.ai.providers.kimi import KimiProvider
from atlas.ai.providers.llama_cpp import LlamaCppProvider
from atlas.ai.providers.openai_base import OpenAICompatibleProvider
from atlas.ai.providers.qwen import QwenProvider

__all__ = [
    # Abstract interfaces & base classes
    "AIProvider",
    "OpenAICompatibleProvider",
    # Data models
    "ChatResponse",
    "Message",
    "MessageRole",
    "ModelInfo",
    "ProviderCapabilities",
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
