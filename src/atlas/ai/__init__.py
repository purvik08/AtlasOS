"""Atlas OS AI Engine package.

This package provides the complete Phase 5 AI Engine:

- :class:`~atlas.ai.manager.AIManager` — lifecycle-managed service; the
  primary entry point for all AI operations.
- :class:`~atlas.ai.providers.base.AIProvider` — abstract provider contract.
- :class:`~atlas.ai.session.ChatSession` / :class:`~atlas.ai.session.SessionManager`
  — conversation session lifecycle.
- :class:`~atlas.ai.history.ConversationHistory` — per-session message store.
- :class:`~atlas.ai.router.AIRouter` — role-based provider selection.
- :class:`~atlas.ai.model.ModelRegistry` — catalog of known models.
- :class:`~atlas.ai.downloader.ModelDownloader` — async model file downloader.

Typical usage::

    from atlas.ai import AIManager
    from atlas.config.settings import AtlasConfig

    manager = AIManager(config)
    await manager.start()

    session = manager.new_session(role="local", model_id="my-model")
    response = await manager.chat(session.session_id, "Hello, Atlas!")
    print(response.message.content)

    await manager.stop()
"""

from atlas.ai.downloader import DownloadResult, ModelDownloader
from atlas.ai.history import ConversationHistory
from atlas.ai.manager import AIManager, AIManagerError, SessionNotFoundError
from atlas.ai.model import ModelNotFoundError, ModelRegistry
from atlas.ai.providers import (
    AIProvider,
    ChatResponse,
    DeepSeekProvider,
    GeminiProvider,
    KimiProvider,
    LlamaCppProvider,
    Message,
    MessageRole,
    ModelInfo,
    ProviderHealth,
    ProviderInfo,
    ProviderRole,
    ProviderStatus,
    QwenProvider,
)
from atlas.ai.router import AIRouter, ProviderNotFoundError
from atlas.ai.session import ChatSession, SessionManager

__all__ = [
    # Manager (primary entry point)
    "AIManager",
    "AIManagerError",
    "SessionNotFoundError",
    # Router
    "AIRouter",
    "ProviderNotFoundError",
    # Sessions
    "ChatSession",
    "SessionManager",
    # History
    "ConversationHistory",
    # Model registry
    "ModelRegistry",
    "ModelNotFoundError",
    # Downloader
    "ModelDownloader",
    "DownloadResult",
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
