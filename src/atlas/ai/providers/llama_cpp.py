"""llama.cpp / GGUF local inference provider stub.

This provider discovers ``.gguf`` model files in the configured ``models_dir``
and exposes them through the :class:`~atlas.ai.providers.base.AIProvider`
interface.  The actual llama-cpp-python inference is **stubbed**: the
interface, model registry integration, and streaming contract are all
production-quality; wiring up ``llama_cpp.Llama`` is left for a later phase
so the rest of the AI engine can be built and tested independently.

When the real backend is ready, replace the ``_stub_*`` helpers with calls to
``llama_cpp.Llama`` — nothing else needs to change.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from atlas.ai.providers.base import (
    AIProvider,
    ChatResponse,
    Message,
    MessageRole,
    ModelInfo,
    ProviderHealth,
    ProviderRole,
    ProviderStatus,
)

logger = logging.getLogger(__name__)

# Sentinel used when no model has been loaded yet.
_NO_MODEL = ""


class LlamaCppProvider(AIProvider):
    """Local GGUF model inference provider backed by llama.cpp.

    Parameters
    ----------
    models_dir:
        Directory to scan for ``.gguf`` files.  Mirrors ``AtlasConfig.models_dir``.
    """

    def __init__(self, models_dir: str | Path = "./models") -> None:
        self._models_dir = Path(models_dir)
        self._loaded_models: dict[str, Path] = {}
        self._discovered: dict[str, ModelInfo] = {}
        logger.debug("LlamaCppProvider initialised with models_dir=%s", self._models_dir)

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:  # noqa: D102
        return "llama_cpp"

    @property
    def role(self) -> ProviderRole:  # noqa: D102
        return ProviderRole.LOCAL

    @property
    def description(self) -> str:  # noqa: D102
        return "Local GGUF model inference via llama.cpp (offline-first)."

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def _discover(self) -> dict[str, ModelInfo]:
        """Scan *models_dir* and return a mapping of model_id → ModelInfo."""
        found: dict[str, ModelInfo] = {}
        if not self._models_dir.exists():
            logger.debug("models_dir %s does not exist; no local models found.", self._models_dir)
            return found

        for path in sorted(self._models_dir.rglob("*.gguf")):
            model_id = path.stem
            size = path.stat().st_size if path.exists() else -1
            found[model_id] = ModelInfo(
                model_id=model_id,
                display_name=model_id.replace("-", " ").replace("_", " ").title(),
                provider_name=self.name,
                loaded=model_id in self._loaded_models,
                size_bytes=size,
                description=f"GGUF model at {path}",
            )
            logger.debug("Discovered GGUF model: %s (%d bytes)", model_id, size)

        return found

    async def list_models(self) -> list[ModelInfo]:  # noqa: D102
        self._discovered = await asyncio.to_thread(self._discover)
        # Sync loaded status.
        for mid in self._loaded_models:
            if mid in self._discovered:
                self._discovered[mid] = self._discovered[mid].model_copy(
                    update={"loaded": True}
                )
        return list(self._discovered.values())

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def load_model(self, model_id: str) -> None:
        """Mark *model_id* as loaded (stub; real llama-cpp load goes here)."""
        if model_id in self._loaded_models:
            logger.debug("Model '%s' is already loaded.", model_id)
            return

        # Refresh discovery before loading.
        await self.list_models()

        if model_id not in self._discovered:
            raise ValueError(
                f"Model '{model_id}' not found in {self._models_dir}. "
                "Ensure the .gguf file is present before loading."
            )

        # STUB: real code would call `llama_cpp.Llama(model_path=path, ...)`
        model_path = self._models_dir / f"{model_id}.gguf"
        self._loaded_models[model_id] = model_path
        logger.info("[STUB] Loaded model '%s' from %s.", model_id, model_path)

    async def unload_model(self, model_id: str) -> None:
        """Release *model_id* resources (stub)."""
        if model_id not in self._loaded_models:
            logger.debug("Model '%s' is not loaded; nothing to unload.", model_id)
            return

        # STUB: real code would call del on the Llama instance and gc.collect().
        del self._loaded_models[model_id]
        logger.info("[STUB] Unloaded model '%s'.", model_id)

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    async def chat(
        self,
        messages: list[Message],
        model_id: str,
        **kwargs: Any,
    ) -> ChatResponse:
        """Return a stubbed chat response."""
        start = time.monotonic()

        if not self._loaded_models:
            logger.warning(
                "chat() called but no model is loaded. "
                "Load a model first with load_model()."
            )

        user_text = messages[-1].content if messages else ""
        stub_reply = (
            f"[llama_cpp STUB] Received: '{user_text}'. "
            f"Real inference via llama-cpp-python is not yet wired. "
            f"Model requested: {model_id!r}."
        )
        latency = (time.monotonic() - start) * 1000

        logger.debug("[STUB] chat() → model=%s, latency=%.1fms", model_id, latency)
        return ChatResponse(
            message=Message(role=MessageRole.ASSISTANT, content=stub_reply),
            provider_name=self.name,
            model_id=model_id,
            prompt_tokens=sum(len(m.content.split()) for m in messages),
            completion_tokens=len(stub_reply.split()),
            latency_ms=latency,
        )

    async def stream_chat(  # type: ignore[override]
        self,
        messages: list[Message],
        model_id: str,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Yield stub tokens one word at a time (simulates streaming)."""
        response = await self.chat(messages, model_id, **kwargs)
        for word in response.message.content.split():
            await asyncio.sleep(0.01)  # simulate token latency
            yield word + " "

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    async def health(self) -> ProviderHealth:
        """Report health based on whether any model is loaded."""
        loaded = list(self._loaded_models.keys())
        status = ProviderStatus.HEALTHY if loaded else ProviderStatus.UNLOADED
        msg = (
            f"{len(loaded)} model(s) loaded: {loaded}"
            if loaded
            else "No models loaded. Use 'atlas model load <model>' to load one."
        )
        return ProviderHealth(
            provider_name=self.name,
            status=status,
            loaded_models=loaded,
            message=msg,
        )
