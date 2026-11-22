"""llama.cpp / GGUF local inference provider.

This provider discovers ``.gguf`` model files in the configured ``models_dir``
and exposes them through the :class:`~atlas.ai.providers.base.AIProvider`
interface. Inference is performed via ``llama-cpp-python``.

Chat prompts are formatted using ChatML tokens:
    <|im_start|>system\n{content}<|im_end|>
    <|im_start|>user\n{content}<|im_end|>
    <|im_start|>assistant\n

Install the backend before loading any model::

    pip install llama-cpp-python
    # On Raspberry Pi 5 (CPU-only, OpenBLAS):
    CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS" \\
        pip install llama-cpp-python

If ``llama_cpp`` is not installed the provider starts up normally but
``load_model`` raises ``RuntimeError`` with an installation hint instead of
crashing the whole AI engine.
"""

from __future__ import annotations

import asyncio
import gc
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


def _build_chatml_prompt(messages: list[Message]) -> str:
    """Format a list of messages into a ChatML prompt string.

    ChatML format (used by Qwen, Mistral-instruct, OpenHermes, etc.)::

        <|im_start|>system
        {system content}<|im_end|>
        <|im_start|>user
        {user content}<|im_end|>
        <|im_start|>assistant

    The trailing ``<|im_start|>assistant\\n`` tells llama.cpp to begin
    generating the assistant reply immediately.
    """
    parts: list[str] = []
    for msg in messages:
        role_tag = msg.role.value  # "system" | "user" | "assistant"
        parts.append(f"<|im_start|>{role_tag}\n{msg.content}<|im_end|>\n")
    parts.append("<|im_start|>assistant\n")
    return "".join(parts)


class LlamaCppProvider(AIProvider):
    """Local GGUF model inference provider backed by llama.cpp.

    Parameters
    ----------
    models_dir:
        Directory to scan for ``.gguf`` files.  Mirrors ``AtlasConfig.models_dir``.
    n_ctx:
        Context window size passed to ``llama_cpp.Llama``.  Defaults to 4096.
    n_gpu_layers:
        Number of layers to offload to GPU.  ``0`` = CPU-only (safe default
        for Raspberry Pi 5).
    """

    def __init__(
        self,
        models_dir: str | Path = "./models",
        n_ctx: int = 4096,
        n_gpu_layers: int = 0,
    ) -> None:
        self._models_dir = Path(models_dir)
        self._n_ctx = n_ctx
        self._n_gpu_layers = n_gpu_layers
        # Maps model_id -> live llama_cpp.Llama instance (not just a path).
        self._loaded_models: dict[str, Any] = {}
        self._discovered: dict[str, ModelInfo] = {}
        logger.debug(
            "LlamaCppProvider initialised with models_dir=%s, n_ctx=%d, n_gpu_layers=%d",
            self._models_dir,
            self._n_ctx,
            self._n_gpu_layers,
        )

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
            logger.debug(
                "models_dir %s does not exist; no local models found.",
                self._models_dir,
            )
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
        """Load *model_id* from disk into memory via llama-cpp-python.

        Raises
        ------
        RuntimeError
            If ``llama-cpp-python`` is not installed.
        ValueError
            If the ``.gguf`` file cannot be found in ``models_dir``.
        RuntimeError
            If llama.cpp fails to load the file (corrupt file, etc.).
        """
        if model_id in self._loaded_models:
            logger.debug("Model '%s' is already loaded.", model_id)
            return

        # Refresh discovery before loading so a freshly-copied file is found.
        await self.list_models()

        if model_id not in self._discovered:
            raise ValueError(
                f"Model '{model_id}' not found in {self._models_dir}. "
                "Ensure the .gguf file is present before loading."
            )

        # Resolve the actual path from the description field set by _discover.
        model_path_str = self._discovered[model_id].description.split(" at ", 1)[-1]
        model_path = Path(model_path_str)

        logger.info("Loading model '%s' from %s …", model_id, model_path)

        try:
            from llama_cpp import Llama  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "llama-cpp-python is not installed. "
                "Install it with: pip install llama-cpp-python\n"
                "On Raspberry Pi 5: "
                "CMAKE_ARGS='-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS' "
                "pip install llama-cpp-python"
            ) from exc

        def _do_load() -> Any:
            return Llama(
                model_path=str(model_path),
                n_ctx=self._n_ctx,
                n_gpu_layers=self._n_gpu_layers,
                verbose=False,
            )

        try:
            llm = await asyncio.to_thread(_do_load)
        except Exception as exc:
            raise RuntimeError(
                f"llama.cpp failed to load '{model_id}' from {model_path}: {exc}"
            ) from exc

        self._loaded_models[model_id] = llm
        logger.info("Model '%s' loaded successfully.", model_id)

    async def unload_model(self, model_id: str) -> None:
        """Release *model_id* from memory and free RAM."""
        if model_id not in self._loaded_models:
            logger.debug("Model '%s' is not loaded; nothing to unload.", model_id)
            return

        llm = self._loaded_models.pop(model_id)
        del llm
        gc.collect()
        logger.info("Model '%s' unloaded and memory released.", model_id)

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    async def chat(
        self,
        messages: list[Message],
        model_id: str,
        **kwargs: Any,
    ) -> ChatResponse:
        """Run a full (non-streaming) inference pass and return the response.

        Parameters
        ----------
        messages:
            Conversation history ending with the latest user message.
        model_id:
            Must be a currently loaded model.
        **kwargs:
            Optional generation overrides: ``max_tokens`` (int, default 512),
            ``temperature`` (float, default 0.7), ``top_p`` (float, default 0.95).
        """
        if model_id not in self._loaded_models:
            raise RuntimeError(
                f"Model '{model_id}' is not loaded. "
                f"Run 'atlas models load {model_id}' first."
            )

        llm = self._loaded_models[model_id]
        prompt = _build_chatml_prompt(messages)

        max_tokens: int = int(kwargs.get("max_tokens", 512))
        temperature: float = float(kwargs.get("temperature", 0.7))
        top_p: float = float(kwargs.get("top_p", 0.95))
        stop_tokens: list[str] = ["<|im_end|>", "<|im_start|>"]

        logger.debug(
            "chat() → model=%s, max_tokens=%d, temperature=%.2f",
            model_id,
            max_tokens,
            temperature,
        )

        start = time.monotonic()

        def _do_inference() -> dict[str, Any]:
            return llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop=stop_tokens,
                echo=False,
            )

        output: dict[str, Any] = await asyncio.to_thread(_do_inference)
        latency = (time.monotonic() - start) * 1000

        reply_text: str = output["choices"][0]["text"]
        usage = output.get("usage", {})
        prompt_tokens: int = usage.get("prompt_tokens", -1)
        completion_tokens: int = usage.get("completion_tokens", -1)

        logger.debug(
            "chat() completed in %.1fms (%d completion tokens).",
            latency,
            completion_tokens,
        )

        return ChatResponse(
            message=Message(role=MessageRole.ASSISTANT, content=reply_text),
            provider_name=self.name,
            model_id=model_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency,
        )

    async def stream_chat(  # type: ignore[override]
        self,
        messages: list[Message],
        model_id: str,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Yield token chunks as they are produced by llama.cpp.

        Each yielded ``str`` is a raw text fragment; callers accumulate them
        to reconstruct the full response.
        """
        if model_id not in self._loaded_models:
            raise RuntimeError(
                f"Model '{model_id}' is not loaded. "
                f"Run 'atlas models load {model_id}' first."
            )

        llm = self._loaded_models[model_id]
        prompt = _build_chatml_prompt(messages)

        max_tokens: int = int(kwargs.get("max_tokens", 512))
        temperature: float = float(kwargs.get("temperature", 0.7))
        top_p: float = float(kwargs.get("top_p", 0.95))
        stop_tokens: list[str] = ["<|im_end|>", "<|im_start|>"]

        logger.debug("stream_chat() → model=%s", model_id)

        # llama.cpp streaming is synchronous; run it in a thread and bridge
        # chunks back to the async caller via an asyncio.Queue.
        queue: asyncio.Queue[str | None] = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def _produce() -> None:
            try:
                stream = llm(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    stop=stop_tokens,
                    echo=False,
                    stream=True,
                )
                for chunk in stream:
                    text: str = chunk["choices"][0]["text"]
                    if text:
                        loop.call_soon_threadsafe(queue.put_nowait, text)
            finally:
                # Signal end-of-stream regardless of success/failure.
                loop.call_soon_threadsafe(queue.put_nowait, None)

        asyncio.get_event_loop().run_in_executor(None, _produce)

        while True:
            token = await queue.get()
            if token is None:
                break
            yield token

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
            else "No models loaded. Use 'atlas models load <model>' to load one."
        )
        return ProviderHealth(
            provider_name=self.name,
            status=status,
            loaded_models=loaded,
            message=msg,
        )
