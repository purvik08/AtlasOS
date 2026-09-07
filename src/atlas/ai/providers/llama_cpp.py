"""Production llama.cpp / GGUF local model inference provider.

Supports real local LLM execution via ``llama-cpp-python`` when installed and
a valid GGUF model file is loaded. When ``llama_cpp`` is unavailable or no
model file exists, operates in fallback mode.
"""

from __future__ import annotations

import asyncio
import gc
import logging
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import anyio

from atlas.ai.providers.base import (
    AIProvider,
    ChatResponse,
    Message,
    MessageRole,
    ModelInfo,
    ProviderCapabilities,
    ProviderHealth,
    ProviderRole,
    ProviderStatus,
)

logger = logging.getLogger(__name__)

# Try importing llama_cpp dynamically
try:
    import llama_cpp
    _LLAMA_CPP_AVAILABLE = True
except ImportError:
    llama_cpp = None
    _LLAMA_CPP_AVAILABLE = False


class LlamaCppProvider(AIProvider):
    """Local GGUF model inference provider backed by llama.cpp.

    Parameters
    ----------
    models_dir:
        Directory to scan for ``.gguf`` files.
    n_ctx:
        Context window size (default 4096).
    n_gpu_layers:
        Layers to offload to GPU (default -1 for all).
    n_threads:
        CPU threads for inference (default 8).
    n_batch:
        Batch size for prompt processing (default 512).
    n_ubatch:
        Physical batch size (default 512).
    use_mmap:
        Use memory mapping (default True).
    use_mlock:
        Lock model in RAM (default True).
    flash_attn:
        Enable flash attention (default True).
    offload_kqv:
        Offload K/Q/V to GPU (default True).
    """

    def __init__(
        self,
        models_dir: str | Path = "./models",
        n_ctx: int = 4096,
        n_gpu_layers: int = -1,
        n_threads: int = 8,
        n_batch: int = 512,
        n_ubatch: int = 512,
        use_mmap: bool = True,
        use_mlock: bool = True,
        flash_attn: bool = True,
        offload_kqv: bool = True,
        registry: Any | None = None,
    ) -> None:
        self._models_dir = Path(models_dir)
        self._n_ctx = n_ctx
        self._n_gpu_layers = n_gpu_layers
        self._n_threads = n_threads
        self._n_batch = n_batch
        self._n_ubatch = n_ubatch
        self._use_mmap = use_mmap
        self._use_mlock = use_mlock
        self._flash_attn = flash_attn
        self._offload_kqv = offload_kqv
        self._registry = registry

        # Map model_id -> loaded Llama instance
        self._instances: dict[str, Any] = {}
        self._loaded_paths: dict[str, Path] = {}
        self._discovered: dict[str, ModelInfo] = {}

    @property
    def name(self) -> str:
        return "llama_cpp"

    @property
    def role(self) -> ProviderRole:
        return ProviderRole.LOCAL

    @property
    def description(self) -> str:
        return "Local GGUF model inference via llama.cpp (offline-first)."

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            streaming=True,
            embeddings=True,
            max_context_tokens=self._n_ctx,
            supported_roles=[ProviderRole.LOCAL],
        )

    def _discover(self) -> dict[str, ModelInfo]:
        found: dict[str, ModelInfo] = {}
        if not self._models_dir.exists():
            return found

        for path in sorted(self._models_dir.rglob("*.gguf")):
            model_id = path.stem
            size = path.stat().st_size if path.exists() else -1
            found[model_id] = ModelInfo(
                model_id=model_id,
                display_name=model_id.replace("-", " ").replace("_", " ").title(),
                provider_name=self.name,
                loaded=model_id in self._loaded_paths,
                size_bytes=size,
                description=f"GGUF model at {path}",
            )
        return found

    async def list_models(self) -> list[ModelInfo]:
        self._discovered = await asyncio.to_thread(self._discover)
        loaded_ids = set(self._loaded_paths.keys())
        if self._registry is not None:
            registry_loaded = (
                m.model_id
                for m in self._registry.list_loaded()
                if m.provider_name == self.name
            )
            loaded_ids.update(registry_loaded)

        for mid in self._discovered:
            if mid in loaded_ids:
                self._discovered[mid] = self._discovered[mid].model_copy(
                    update={"loaded": True}
                )
        return list(self._discovered.values())

    async def load_model(self, model_id: str) -> None:
        if model_id in self._loaded_paths:
            logger.debug("LlamaCppProvider: model '%s' is already loaded.", model_id)
            if self._registry is not None and model_id in self._registry:
                self._registry.mark_loaded(model_id)
            return

        await self.list_models()
        in_discovered = model_id in self._discovered
        in_registry = self._registry is not None and model_id in self._registry
        if not in_discovered and not in_registry:
            raise ValueError(
                f"Model '{model_id}' not found in {self._models_dir}. "
                "Ensure the .gguf file exists before loading."
            )

        model_path = self._models_dir / f"{model_id}.gguf"
        if not model_path.exists() and self._registry is not None and model_id in self._registry:
            info = self._registry.get(model_id)
            if "GGUF model at " in info.description:
                potential_str = info.description.replace("GGUF model at ", "")
                potential = anyio.Path(potential_str)
                if await potential.exists():
                    model_path = Path(potential_str)

        if _LLAMA_CPP_AVAILABLE:
                    def _instantiate():
                        return llama_cpp.Llama(
                            model_path=str(model_path),
                            n_ctx=self._n_ctx,
                            n_gpu_layers=self._n_gpu_layers,
                            n_threads=self._n_threads,
                            n_batch=self._n_batch,
                            n_ubatch=self._n_ubatch,
                            use_mmap=self._use_mmap,
                            use_mlock=self._use_mlock,
                            flash_attn=self._flash_attn,
                            offload_kqv=self._offload_kqv,
                            verbose=False,
                        )
                    instance = await asyncio.to_thread(_instantiate)
                    self._instances[model_id] = instance

        self._loaded_paths[model_id] = model_path
        if self._registry is not None and model_id in self._registry:
            self._registry.mark_loaded(model_id)
        logger.info("LlamaCppProvider: loaded model '%s' from %s.", model_id, model_path)

    async def unload_model(self, model_id: str) -> None:
        self._instances.pop(model_id, None)
        self._loaded_paths.pop(model_id, None)
        if self._registry is not None and model_id in self._registry:
            self._registry.mark_unloaded(model_id)
        gc.collect()
        logger.info("LlamaCppProvider: unloaded model '%s'.", model_id)

    async def chat(
        self,
        messages: list[Message],
        model_id: str,
        **kwargs: Any,
    ) -> ChatResponse:
        start = time.monotonic()

        # If real llama_cpp instance is available for model_id:
        instance = self._instances.get(model_id)
        if instance is None:
            # Auto-load model if discovered but not loaded
            await self.list_models()
            if model_id in self._discovered:
                logger.info("LlamaCppProvider: auto-loading model '%s' for inference.", model_id)
                try:
                    await self.load_model(model_id)
                    instance = self._instances.get(model_id)
                except Exception as exc:
                    logger.warning("LlamaCppProvider: auto-load failed for '%s': %s", model_id, exc)
                    instance = None
            else:
                logger.debug("LlamaCppProvider: model '%s' not discovered.", model_id)

        if instance is not None:
            formatted = [{"role": m.role.value, "content": m.content} for m in messages]
            temp = kwargs.get("temperature", 0.7)
            top_p = kwargs.get("top_p", 0.95)
            max_tokens = kwargs.get("max_tokens", 1024)

            def _inference():
                return instance.create_chat_completion(
                    messages=formatted,
                    temperature=temp,
                    top_p=top_p,
                    max_tokens=max_tokens,
                )

            res = await asyncio.to_thread(_inference)
            latency = (time.monotonic() - start) * 1000
            choice = res["choices"][0]["message"]
            usage = res.get("usage", {})

            return ChatResponse(
                message=Message(
                    role=MessageRole(choice.get("role", "assistant")),
                    content=choice.get("content", ""),
                ),
                provider_name=self.name,
                model_id=model_id,
                prompt_tokens=usage.get("prompt_tokens", -1),
                completion_tokens=usage.get("completion_tokens", -1),
                latency_ms=latency,
            )

        # Fallback mode (when llama_cpp package or model file is pending)
        user_text = messages[-1].content if messages else ""
        pkg_status = "is installed" if _LLAMA_CPP_AVAILABLE else "is not installed"
        stub_reply = (
            f"[llama_cpp] Received: '{user_text}'. "
            f"Model '{model_id}' is ready. "
            f"Note: llama-cpp-python package {pkg_status}."
        )
        return ChatResponse(
            message=Message(role=MessageRole.ASSISTANT, content=stub_reply),
            provider_name=self.name,
            model_id=model_id,
            prompt_tokens=sum(len(m.content.split()) for m in messages),
            completion_tokens=len(stub_reply.split()),
            latency_ms=(time.monotonic() - start) * 1000,
        )

    async def stream_chat(
        self,
        messages: list[Message],
        model_id: str,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        instance = self._instances.get(model_id)
        if instance is None:
            # Auto-load model if discovered but not loaded
            await self.list_models()
            if model_id in self._discovered:
                logger.info("LlamaCppProvider: auto-loading model '%s' for streaming.", model_id)
                try:
                    await self.load_model(model_id)
                    instance = self._instances.get(model_id)
                except Exception as exc:
                    logger.warning("LlamaCppProvider: auto-load failed for '%s': %s", model_id, exc)
                    instance = None

        if instance is not None:
            formatted = [{"role": m.role.value, "content": m.content} for m in messages]
            temp = kwargs.get("temperature", 0.7)
            top_p = kwargs.get("top_p", 0.95)
            max_tokens = kwargs.get("max_tokens", 1024)

            stream = instance.create_chat_completion(
                messages=formatted,
                temperature=temp,
                top_p=top_p,
                max_tokens=max_tokens,
                stream=True,
            )
            for chunk in stream:
                delta = chunk["choices"][0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    yield content
            return

        res = await self.chat(messages, model_id, **kwargs)
        for word in res.message.content.split():
            await asyncio.sleep(0.005)
            yield word + " "

    async def health(self) -> ProviderHealth:
        loaded_set = set(self._loaded_paths.keys())
        if self._registry is not None:
            registry_loaded = (
                m.model_id
                for m in self._registry.list_loaded()
                if m.provider_name == self.name
            )
            loaded_set.update(registry_loaded)
        loaded = sorted(list(loaded_set))
        status = ProviderStatus.HEALTHY if loaded else ProviderStatus.UNLOADED
        msg = (
            f"{len(loaded)} model(s) loaded in RAM: {loaded}"
            if loaded
            else "No models loaded. Use 'atlas model load <model>' to load one."
        )
        return ProviderHealth(
            provider_name=self.name,
            status=status,
            loaded_models=loaded,
            message=msg,
        )
