"""Top-level AI Engine orchestrator for Atlas OS.

:class:`AIManager` is the **single entry point** for all AI operations —
CLI, UI, REST API, and Voice must never call providers, the router, or
the inference engine directly.

Architecture
------------
::

    CLI / UI / API / Voice
          |
      AIManager  (IService singleton, owns all subsystems)
          |
     InferenceEngine
          |
       AIRouter
          |
       Provider  (stateless — llama_cpp | gemini | deepseek | qwen | kimi)

Subsystems managed internally
------------------------------
* :class:`~atlas.ai.router.AIRouter` — provider selection.
* :class:`~atlas.ai.engine.InferenceEngine` — retries, timeouts, caching pipeline.
* :class:`~atlas.ai.session.SessionManager` — per-session conversation history.
* :class:`~atlas.ai.prompt.PromptManager` — prompt construction and templates.
* :class:`~atlas.ai.model.ModelRegistry` — single source of truth for known models.
* :class:`~atlas.ai.downloader.ModelDownloader` — chunked HTTP downloads with resume.
* :class:`~atlas.ai.cache.CacheManager` — SHA-256 keyed response cache.
* :class:`~atlas.ai.resource.ResourceManager` — RAM/CPU guard before loading models.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from atlas.ai.cache import CacheManager
from atlas.ai.downloader import DownloadResult, ModelDownloader
from atlas.ai.engine import InferenceEngine
from atlas.ai.history import ConversationHistory  # noqa: F401 – re-exported
from atlas.ai.model import ModelRegistry
from atlas.ai.prompt import PromptManager
from atlas.ai.providers.base import (
    AIProvider,
    ChatResponse,
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
from atlas.ai.resource import ResourceLimitError, ResourceManager
from atlas.ai.router import AIRouter
from atlas.ai.session import ChatSession, SessionManager
from atlas.config.settings import AtlasConfig
from atlas.runtime.health import HealthStatus, ServiceHealth
from atlas.runtime.registry import IService

logger = logging.getLogger(__name__)


class AIManagerError(Exception):
    """Base exception for AIManager failures."""


class SessionNotFoundError(AIManagerError):
    """Raised when a session_id is not found in the manager."""


class InvalidModelOperationError(AIManagerError, ValueError):
    """Raised when an operation is invalid for the target model's provider role.

    For example, loading or downloading a cloud model — operations that are
    only meaningful for local (llama.cpp / GGUF) models.
    """


class AIManager(IService):
    """Lifecycle-managed AI Engine service — the single entry point for all AI.

    Register with :class:`~atlas.runtime.registry.ServiceRegistry` via
    ``app.register_service(AIManager(config))`` before calling
    ``app.start()``.

    Parameters
    ----------
    config:
        The application-wide Atlas config.
    """

    dependencies: tuple[str, ...] = ()

    def __init__(self, config: AtlasConfig) -> None:
        self._config = config
        ai_cfg = getattr(config, "ai", None)

        self._router = AIRouter(
            default_role=ProviderRole(getattr(ai_cfg, "default_role", "auto"))
        )
        # Use the split local/cloud layout for clean separation between the
        # local GGUF catalog and the cloud API catalog.  Tests that pass
        # their own persistence_path continue to work.
        self._model_registry = ModelRegistry(data_dir=getattr(config, "data_dir", "./data"))
        self._prompt_manager = PromptManager()
        self._cache_manager = CacheManager(
            enabled=getattr(ai_cfg, "cache_enabled", True),
            ttl_seconds=getattr(ai_cfg, "cache_ttl_seconds", 3600),
        )
        self._resource_manager = ResourceManager(
            max_ram_percent=getattr(ai_cfg, "max_ram_percent", 90.0)
        )
        self._session_manager = SessionManager(
            max_history_messages=getattr(ai_cfg, "max_history_messages", 50)
        )
        self._inference_engine = InferenceEngine(
            router=self._router,
            cache_manager=self._cache_manager,
            prompt_manager=self._prompt_manager,
            max_retries=getattr(ai_cfg, "max_retries", 3),
            timeout_seconds=getattr(ai_cfg, "timeout_seconds", 60.0),
        )
        self._downloader = ModelDownloader(
            models_dir=config.models_dir,
            registry=self._model_registry,
        )
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
        if self._started:
            return
        logger.info("AIManager: starting AI Engine.")
        
        # Sync stored API keys to config before creating providers
        from atlas.secrets import sync_secrets_to_config
        sync_secrets_to_config(self._config)
        
        ai_cfg = getattr(self._config, "ai", None)

        providers: list[AIProvider] = [
                    LlamaCppProvider(
                        models_dir=self._config.models_dir,
                        n_ctx=getattr(ai_cfg, "n_ctx", 4096),
                        n_gpu_layers=getattr(ai_cfg, "n_gpu_layers", -1),
                        n_threads=getattr(ai_cfg, "n_threads", 8),
                        n_batch=getattr(ai_cfg, "n_batch", 512),
                        n_ubatch=getattr(ai_cfg, "n_ubatch", 512),
                        use_mmap=getattr(ai_cfg, "use_mmap", True),
                        use_mlock=getattr(ai_cfg, "use_mlock", True),
                        flash_attn=getattr(ai_cfg, "flash_attn", True),
                        offload_kqv=getattr(ai_cfg, "offload_kqv", True),
                        registry=self._model_registry,
                    ),
                    GeminiProvider(
                api_key=getattr(ai_cfg, "gemini_api_key", ""),
                timeout_seconds=getattr(ai_cfg, "timeout_seconds", 60.0),
            ),
            DeepSeekProvider(
                api_key=getattr(ai_cfg, "deepseek_api_key", ""),
                timeout_seconds=getattr(ai_cfg, "timeout_seconds", 60.0),
            ),
            KimiProvider(
                api_key=getattr(ai_cfg, "kimi_api_key", ""),
                timeout_seconds=getattr(ai_cfg, "timeout_seconds", 60.0),
            ),
            QwenProvider(
                api_key=getattr(ai_cfg, "qwen_api_key", ""),
                timeout_seconds=getattr(ai_cfg, "timeout_seconds", 60.0),
            ),
        ]

        for provider in providers:
            self._router.register(provider)
            logger.info("AIManager: registered provider '%s'.", provider.name)
            try:
                models = await provider.list_models()
                for m in models:
                    if m.model_id in self._model_registry:
                        existing = self._model_registry.get(m.model_id)
                        if existing.loaded:
                            m = m.model_copy(update={"loaded": True})
                    self._model_registry.register(m, overwrite=True)
            except Exception:
                logger.exception(
                    "AIManager: failed to list models for provider '%s'.", provider.name
                )

        # Scan local models_dir for any GGUF files.
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

        from atlas.ai.providers.base import ProviderStatus

        unhealthy: list[str] = []
        for pname in self._router.registered_names():
            try:
                ph = await self._router.get(pname).health()
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
        """Create a new chat session and return it."""
        effective_role = ProviderRole(role) if role else None
        provider = self._router.select(
            provider_name=provider_name, role=effective_role
        )

        if model_id is None:
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
            session.session_id, provider.name, model_id,
        )
        return session

    def get_session(self, session_id: str) -> ChatSession:
        """Retrieve an existing session by ID."""
        try:
            return self._session_manager.get(session_id)
        except KeyError as exc:
            raise SessionNotFoundError(str(exc)) from exc

    def delete_session(self, session_id: str) -> None:
        """Delete a session and its history."""
        try:
            self._session_manager.delete(session_id)
        except KeyError as exc:
            raise SessionNotFoundError(str(exc)) from exc

    def list_sessions(self) -> list[ChatSession]:
        """Return all active sessions ordered by creation time."""
        return self._session_manager.list_all()

    # ------------------------------------------------------------------
    # Inference — routed through InferenceEngine (NEVER call providers directly)
    # ------------------------------------------------------------------

    async def chat(
        self,
        session_id: str,
        user_message: str,
        **kwargs: Any,
    ) -> ChatResponse:
        """Send a message and receive a complete response via InferenceEngine."""
        session = self.get_session(session_id)
        session.add_user_message(user_message)

        response = await self._inference_engine.execute_chat(
            messages=session.get_messages(),
            model_id=session.model_id,
            provider_name=session.provider_name,
            system_prompt=session.system_prompt,
            **kwargs,
        )

        session.add_assistant_message(response.message.content)
        logger.debug(
            "AIManager: chat in session %s -> %d tokens.",
            session_id, response.completion_tokens,
        )
        return response

    async def stream_chat(
        self,
        session_id: str,
        user_message: str,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream chat tokens via InferenceEngine."""
        session = self.get_session(session_id)
        session.add_user_message(user_message)

        accumulated: list[str] = []
        async for chunk in self._inference_engine.execute_stream_chat(
            messages=session.get_messages(),
            model_id=session.model_id,
            provider_name=session.provider_name,
            system_prompt=session.system_prompt,
            **kwargs,
        ):
            accumulated.append(chunk)
            yield chunk

        session.add_assistant_message("".join(accumulated))

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
        """Return the health report for *provider_name*."""
        provider = self._router.get(provider_name)
        return await provider.health()

    # ------------------------------------------------------------------
    # Model management — delegated through ModelRegistry & providers
    # ------------------------------------------------------------------

    def list_models(self) -> list[ModelInfo]:
        """Return all known models from the registry (single source of truth)."""
        return self._model_registry.list_all()

    # ------------------------------------------------------------------
    # Local/Cloud separation guards
    # ------------------------------------------------------------------

    # Operations that are only valid for local (llama.cpp / GGUF) providers.
    # Downloading a cloud model has no meaningful artifact; loading a cloud
    # model would invoke the local RAM resource check against a remote service.
    _LOCAL_ONLY_OPERATIONS = frozenset({"load", "download"})

    def _resolve_provider_role(
        self, model_id: str, provider_name: str | None
    ) -> tuple[str, ProviderRole]:
        """Return ``(provider_name, role)`` for *model_id*, defaulting by ID if missing."""
        if provider_name is None:
            info = self._model_registry.get(model_id)
            provider_name = info.provider_name
        provider = self._router.get(provider_name)
        return provider.name, provider.role

    def _guard_local_only_operation(
        self,
        operation: str,
        *,
        model_id: str | None = None,
        provider_name: str | None = None,
    ) -> None:
        """Reject operations that are only valid on local (llama.cpp) providers.

        Raises
        ------
        InvalidModelOperationError
            With a clear, actionable message naming the provider and pointing
            the user to the correct alternative command.
        """
        if operation not in self._LOCAL_ONLY_OPERATIONS:
            return  # not a guarded operation

        # download_model has no registry entry yet — we only know the URL, not
        # which provider owns the model_id. We use a safe default: only the
        # ``llama_cpp`` provider is local; everything else is cloud and is
        # rejected here. Explicit provider_name override is supported.
        if operation == "download":
            # Always require an explicit provider for downloads to keep the
            # caller explicit about what they intend to fetch.
            target_provider = provider_name or "llama_cpp"
            try:
                provider = self._router.get(target_provider)
            except Exception as exc:  # noqa: BLE001
                raise InvalidModelOperationError(
                    f"Cannot download model '{model_id}': provider '{target_provider}' "
                    f"is not registered. Registered providers: "
                    f"{self._router.registered_names()}."
                ) from exc
            if provider.role is not ProviderRole.LOCAL:
                raise InvalidModelOperationError(
                    f"Cannot download model '{model_id}': provider '{provider.name}' is "
                    f"a cloud provider. Only local GGUF (llama.cpp) models can be "
                    f"downloaded. For cloud models, configure "
                    f"{f'ATLAS_AI__{provider.name.upper()}_API_KEY'} and use "
                    f"'atlas provider health {provider.name}'."
                )
            return

        # load/unload: resolve from registry, then refuse CLOUD.
        resolved_name, role = self._resolve_provider_role(model_id, provider_name)
        if role is ProviderRole.CLOUD:
            env_var = f"ATLAS_AI__{resolved_name.upper()}_API_KEY"
            raise InvalidModelOperationError(
                f"Cannot {operation} model '{model_id}': provider '{resolved_name}' is a "
                f"cloud provider. Cloud models do not require a local "
                f"load/unload lifecycle — they execute remotely via API. "
                f"Configure your API key ({env_var}) and check status using "
                f"'atlas provider health {resolved_name}'."
            )

    async def load_model(self, model_id: str, provider_name: str | None = None) -> None:
        """Load *model_id* via its owning provider, checking resources first.

        Refuses with :class:`InvalidModelOperationError` if the resolved
        provider is a cloud provider; cloud models do not have a local
        load/unload lifecycle.
        """
        self._guard_local_only_operation("load", model_id=model_id, provider_name=provider_name)

        if provider_name is None:
            info = self._model_registry.get(model_id)
            provider_name = info.provider_name

        # Check resources before loading
        model_info = self._model_registry.get(model_id)
        try:
            self._resource_manager.check_allocation_safety(
                required_bytes=model_info.size_bytes if model_info.size_bytes > 0 else -1
            )
        except ResourceLimitError as exc:
            logger.error("AIManager: resource limit exceeded for model '%s': %s", model_id, exc)
            raise

        provider = self._router.get(provider_name)
        await provider.load_model(model_id)
        self._model_registry.mark_loaded(model_id)
        logger.info("AIManager: loaded model '%s' via '%s'.", model_id, provider_name)

    async def unload_model(self, model_id: str, provider_name: str | None = None) -> None:
        """Unload *model_id* via its owning provider.

        Refuses with :class:`InvalidModelOperationError` if the resolved
        provider is a cloud provider; cloud models do not have a local
        unload lifecycle.
        """
        self._guard_local_only_operation("unload", model_id=model_id, provider_name=provider_name)
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
        provider_name: str | None = None,
        **kwargs: Any,
    ) -> DownloadResult:
        """Download *model_id* from *source_url* into ``models_dir``.

        Refuses with :class:`InvalidModelOperationError` when the resolved
        provider is not the local ``llama_cpp`` provider — only local GGUF
        (llama.cpp) models can be downloaded.
        """
        self._guard_local_only_operation(
            "download", model_id=model_id, provider_name=provider_name
        )
        result = await self._downloader.download(model_id, source_url, **kwargs)
        if result.success:
            self._model_registry.scan(self._config.models_dir)
        return result

    # ------------------------------------------------------------------
    # Accessors (for CLI / tests — no DI consumers should use these)
    # ------------------------------------------------------------------

    @property
    def router(self) -> AIRouter:
        return self._router

    @property
    def session_manager(self) -> SessionManager:
        return self._session_manager

    @property
    def model_registry(self) -> ModelRegistry:
        return self._model_registry

    @property
    def downloader(self) -> ModelDownloader:
        return self._downloader

    @property
    def prompt_manager(self) -> PromptManager:
        return self._prompt_manager

    @property
    def cache_manager(self) -> CacheManager:
        return self._cache_manager

    @property
    def resource_manager(self) -> ResourceManager:
        return self._resource_manager

    @property
    def inference_engine(self) -> InferenceEngine:
        return self._inference_engine

    def __repr__(self) -> str:
        return (
            f"AIManager(providers={self._router.registered_names()!r}, "
            f"sessions={self._session_manager.count()}, "
            f"models={len(self._model_registry)})"
        )
