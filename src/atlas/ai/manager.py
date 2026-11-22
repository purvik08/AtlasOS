"""Top-level AI Engine orchestrator for Atlas OS.

:class:`AIManager` is the single entry point for all AI operations.  It
implements :class:`~atlas.runtime.registry.IService` so it integrates
seamlessly with the Runtime Core's service lifecycle — started by
``AtlasApplication`` just like every other service.

Responsibilities
----------------
* Instantiate and register all AI providers on ``start()``.
* Expose a unified chat/stream API that delegates to the router.
* Manage the session lifecycle via :class:`~atlas.ai.session.SessionManager`.
* Keep the model registry up-to-date.
* Report its own health to the runtime health monitor.

Dependency injection
--------------------
``AIManager`` receives ``AtlasConfig`` through the constructor.  It creates its
own ``AIRouter``, ``SessionManager``, ``ModelRegistry``, and ``ModelDownloader``
internally rather than expecting them from the DI container, because they are
internal implementation details not needed by other services.

If a provider needs to be replaced or extended (e.g. adding Ollama), register
a new :class:`~atlas.ai.providers.base.AIProvider` subclass — the manager
discovers them without code changes.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from atlas.ai.downloader import DownloadResult, ModelDownloader
from atlas.ai.history import ConversationHistory  # noqa: F401 – re-exported
from atlas.ai.model import ModelRegistry
from atlas.ai.providers.base import (
    AIProvider,
    ChatResponse,
    Message,
    MessageRole,
    ModelInfo,
    ProviderHealth,
    ProviderInfo,
    ProviderRole,
)
from atlas.ai.providers.deepseek import DeepSeekProvider
from atlas.ai.providers.gemini import GeminiProvider
from atlas.ai.providers.kimi import KimiProvider
from atlas.ai.providers.llama_cpp import LlamaCppProvider
from atlas.ai.providers.qwen import QwenProvider
from atlas.ai.router import AIRouter, ProviderNotFoundError
from atlas.ai.session import ChatSession, SessionManager
from atlas.config.settings import AtlasConfig
from atlas.runtime.health import HealthStatus, ServiceHealth
from atlas.runtime.registry import IService

logger = logging.getLogger(__name__)


class AIManagerError(Exception):
    """Base exception for AIManager failures."""


class SessionNotFoundError(AIManagerError):
    """Raised when a session_id is not found in the manager."""


class AIManager(IService):
    """Lifecycle-managed AI Engine service.

    Register with :class:`~atlas.runtime.registry.ServiceRegistry` via
    ``app.register_service(AIManager(config))`` before calling
    ``app.start()``.

    Parameters
    ----------
    config:
        The application-wide Atlas config.  The manager reads
        ``config.ai``, ``config.models_dir``, and related fields.
    """

    dependencies: tuple[str, ...] = ()  # no runtime dependencies required

    def __init__(self, config: AtlasConfig) -> None:
        self._config = config
        self._router = AIRouter(
            default_role=ProviderRole(getattr(config.ai, "default_role", "auto"))
        )
        self._session_manager = SessionManager(
            max_history_messages=getattr(config.ai, "max_history_messages", 50)
        )
        self._model_registry = ModelRegistry()
        self._downloader = ModelDownloader(models_dir=config.models_dir)
        self._started = False
        logger.debug("AIManager created.")

    # ------------------------------------------------------------------
    # IService implementation
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "ai_manager"

    async def start(self) -> None:
        """Instantiate and register all providers; populate the model registry."""
        logger.info("AIManager: starting AI Engine.")
        ai_cfg = getattr(self._config, "ai", None)

        # Build providers using API keys from config (or empty = stubbed).
        providers: list[AIProvider] = [
            LlamaCppProvider(models_dir=self._config.models_dir),
            GeminiProvider(api_key=getattr(ai_cfg, "gemini_api_key", "")),
            DeepSeekProvider(api_key=getattr(ai_cfg, "deepseek_api_key", "")),
            KimiProvider(api_key=getattr(ai_cfg, "kimi_api_key", "")),
            QwenProvider(api_key=getattr(ai_cfg, "qwen_api_key", "")),
        ]

        for provider in providers:
            self._router.register(provider)
            logger.info("AIManager: registered provider '%s'.", provider.name)
            # Populate the model registry from each provider.
            try:
                models = await provider.list_models()
                for m in models:
                    self._model_registry.register(m, overwrite=True)
            except Exception:
                logger.exception(
                    "AIManager: failed to list models for provider '%s'.", provider.name
                )

        # Also scan models_dir for GGUF files not reported by llama_cpp yet.
        self._model_registry.scan(self._config.models_dir)

        self._started = True
        logger.info(
            "AIManager: started. Providers: %s. Models known: %d.",
            self._router.registered_names(),
            len(self._model_registry),
        )

    async def stop(self) -> None:
        """Gracefully unload all models and shut down providers."""
        logger.info("AIManager: stopping AI Engine.")
        for name in self._router.registered_names():
            try:
                provider = self._router.get(name)
                health = await provider.health()
                for model_id in health.loaded_models:
                    await provider.unload_model(model_id)
            except Exception:
                logger.exception("AIManager: error stopping provider '%s'.", name)

        self._started = False
        logger.info("AIManager: stopped.")

    async def health_check(self) -> ServiceHealth:
        """Aggregate provider health into a single service health status."""
        if not self._started:
            return ServiceHealth(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message="AIManager has not been started.",
            )

        unhealthy: list[str] = []
        for pname in self._router.registered_names():
            try:
                ph = await self._router.get(pname).health()
                from atlas.ai.providers.base import ProviderStatus

                if ph.status is ProviderStatus.UNHEALTHY:
                    unhealthy.append(pname)
            except Exception:
                unhealthy.append(pname)

        if unhealthy:
            return ServiceHealth(
                name=self.name,
                status=HealthStatus.DEGRADED,
                message=f"Unhealthy providers: {unhealthy}",
            )
        return ServiceHealth(name=self.name, status=HealthStatus.HEALTHY)

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def new_session(
        self,
        *,
        provider_name: str | None = None,
        role: str | None = None,
        model_id: str | None = None,
        system_prompt: str = "",
        metadata: dict | None = None,
    ) -> ChatSession:
        """Create a new chat session.

        Parameters
        ----------
        provider_name:
            Explicit provider to use.  Mutually exclusive with *role*.
        role:
            Role string (``"local"``, ``"cloud"``, ``"auto"``).
        model_id:
            Model to use.  When ``None``, uses the provider's first model.
        system_prompt:
            Instruction prepended to every inference call.
        metadata:
            Arbitrary key/value metadata.

        Returns
        -------
        ChatSession
        """
        effective_role = ProviderRole(role) if role else None
        provider = self._router.select(
            provider_name=provider_name, role=effective_role
        )

        if model_id is None:
            # Pick a sensible default model.
            ai_cfg = getattr(self._config, "ai", None)
            model_id = getattr(ai_cfg, "default_provider", provider.name)

        session = self._session_manager.create(
            provider_name=provider.name,
            model_id=model_id,
            system_prompt=system_prompt,
            metadata=metadata,
        )
        logger.info(
            "AIManager: new session %s (provider=%s, model=%s).",
            session.session_id,
            provider.name,
            model_id,
        )
        return session

    def get_session(self, session_id: str) -> ChatSession:
        """Retrieve an existing session.

        Raises
        ------
        SessionNotFoundError
        """
        try:
            return self._session_manager.get(session_id)
        except KeyError as exc:
            raise SessionNotFoundError(str(exc)) from exc

    def delete_session(self, session_id: str) -> None:
        """Delete a session and its history.

        Raises
        ------
        SessionNotFoundError
        """
        try:
            self._session_manager.delete(session_id)
        except KeyError as exc:
            raise SessionNotFoundError(str(exc)) from exc

    def list_sessions(self) -> list[ChatSession]:
        """Return all active sessions ordered by creation time."""
        return self._session_manager.list_all()

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    async def chat(
        self,
        session_id: str,
        user_message: str,
        **kwargs: Any,
    ) -> ChatResponse:
        """Send a message and receive a complete response.

        Parameters
        ----------
        session_id:
            The session to chat in.
        user_message:
            The user's text input.
        **kwargs:
            Passed verbatim to the provider's ``chat()`` method.

        Returns
        -------
        ChatResponse

        Raises
        ------
        SessionNotFoundError
        ProviderNotFoundError
        """
        session = self.get_session(session_id)
        session.add_user_message(user_message)

        provider = self._router.get(session.provider_name)
        messages = session.get_messages()
        response = await provider.chat(messages, model_id=session.model_id, **kwargs)

        session.add_assistant_message(response.message.content)
        logger.debug(
            "AIManager: chat in session %s → %d tokens.",
            session_id,
            response.completion_tokens,
        )
        return response

    async def stream_chat(
        self,
        session_id: str,
        user_message: str,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Send a message and stream back token chunks.

        Yields ``str`` token fragments.  The assistant message is appended to
        history only after the stream is fully consumed.

        Raises
        ------
        SessionNotFoundError
        ProviderNotFoundError
        """
        session = self.get_session(session_id)
        session.add_user_message(user_message)

        provider = self._router.get(session.provider_name)
        messages = session.get_messages()

        accumulated: list[str] = []
        async for chunk in provider.stream_chat(
            messages, model_id=session.model_id, **kwargs
        ):
            accumulated.append(chunk)
            yield chunk

        full_text = "".join(accumulated)
        session.add_assistant_message(full_text)
        logger.debug(
            "AIManager: stream_chat in session %s completed (%d chars).",
            session_id,
            len(full_text),
        )

    # ------------------------------------------------------------------
    # Provider inspection
    # ------------------------------------------------------------------

    def list_providers(self) -> list[ProviderInfo]:
        """Return descriptors for all registered providers."""
        return [
            self._router.get(name).info()
            for name in self._router.registered_names()
        ]

    async def provider_health(self, provider_name: str) -> ProviderHealth:
        """Return the health report for *provider_name*.

        Raises
        ------
        ProviderNotFoundError
        """
        provider = self._router.get(provider_name)
        return await provider.health()

    # ------------------------------------------------------------------
    # Model management
    # ------------------------------------------------------------------

    def list_models(self) -> list[ModelInfo]:
        """Return all known models from the registry."""
        return self._model_registry.list_all()

    async def load_model(self, model_id: str, provider_name: str | None = None) -> None:
        """Load *model_id* via its owning provider.

        Parameters
        ----------
        model_id:
            ID of the model to load.
        provider_name:
            Provider to use.  If ``None``, the registry is consulted to find
            the owning provider.

        Raises
        ------
        ModelNotFoundError / ValueError / ProviderNotFoundError
        """
        if provider_name is None:
            info = self._model_registry.get(model_id)
            provider_name = info.provider_name

        provider = self._router.get(provider_name)
        await provider.load_model(model_id)
        self._model_registry.mark_loaded(model_id)
        logger.info("AIManager: loaded model '%s' via '%s'.", model_id, provider_name)

    async def unload_model(self, model_id: str, provider_name: str | None = None) -> None:
        """Unload *model_id* via its owning provider."""
        if provider_name is None:
            info = self._model_registry.get(model_id)
            provider_name = info.provider_name

        provider = self._router.get(provider_name)
        await provider.unload_model(model_id)
        self._model_registry.mark_unloaded(model_id)
        logger.info("AIManager: unloaded model '%s'.", model_id)

    async def download_model(
        self,
        model_id: str,
        source_url: str,
        **kwargs: Any,
    ) -> DownloadResult:
        """Download *model_id* from *source_url* into ``models_dir``."""
        result = await self._downloader.download(model_id, source_url, **kwargs)
        if result.success:
            self._model_registry.scan(self._config.models_dir)
        return result

    # ------------------------------------------------------------------
    # Accessors (for CLI / tests)
    # ------------------------------------------------------------------

    @property
    def router(self) -> AIRouter:
        """The internal provider router."""
        return self._router

    @property
    def session_manager(self) -> SessionManager:
        """The internal session manager."""
        return self._session_manager

    @property
    def model_registry(self) -> ModelRegistry:
        """The internal model registry."""
        return self._model_registry

    @property
    def downloader(self) -> ModelDownloader:
        """The internal model downloader."""
        return self._downloader

    def __repr__(self) -> str:
        return (
            f"AIManager(providers={self._router.registered_names()!r}, "
            f"sessions={self._session_manager.count()}, "
            f"models={len(self._model_registry)})"
        )
