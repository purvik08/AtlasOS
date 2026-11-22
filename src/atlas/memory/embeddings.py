"""Embedding providers for Atlas OS memory system."""

from __future__ import annotations

import hashlib
import os
from abc import ABC, abstractmethod
from typing import Any

# Optional import for loguru
try:
    from loguru import logger
    LOGURU_AVAILABLE = True
except ImportError:
    LOGURU_AVAILABLE = False
    import logging
    logger = logging.getLogger(__name__)

# Try to import sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None

# Try to import torch
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        pass

    @abstractmethod
    def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return embedding dimension."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return provider name."""
        pass


class HashingEmbedder(EmbeddingProvider):
    """Fallback embedder using simple hashing (deterministic, low quality)."""

    def __init__(self, dimension: int = 384) -> None:
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def name(self) -> str:
        return "hashing"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_single(text) for text in texts]

    def embed_single(self, text: str) -> list[float]:
        # Simple deterministic hash-based embedding
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()

        # Expand to desired dimension
        embedding = []
        for i in range(self._dimension):
            byte_idx = i % len(hash_bytes)
            embedding.append((hash_bytes[byte_idx] / 255.0) * 2 - 1)  # [-1, 1]

        return embedding


class SentenceTransformersEmbedder(EmbeddingProvider):
    """Embedder using sentence-transformers models."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str | None = None) -> None:
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise RuntimeError("sentence-transformers not installed")

        self._model_name = model_name
        self._device = device or ("cuda" if TORCH_AVAILABLE and torch.cuda.is_available() else "cpu")
        self._model = None

    @property
    def dimension(self) -> int:
        if self._model:
            return self._model.get_sentence_embedding_dimension()
        # Default for all-MiniLM-L6-v2
        return 384

    @property
    def name(self) -> str:
        return f"sentence-transformers/{self._model_name}"

    def _load_model(self) -> None:
        """Lazy load the model."""
        if self._model is None:
            if LOGURU_AVAILABLE:
                logger.info(f"Loading embedding model: {self._model_name} on {self._device}")
            else:
                logger.info(f"Loading embedding model: {self._model_name} on {self._device}")
            self._model = SentenceTransformer(self._model_name, device=self._device)

    def embed(self, texts: list[str]) -> list[list[float]]:
        self._load_model()
        embeddings = self._model.encode(texts, convert_to_tensor=False, show_progress_bar=False)
        return [emb.tolist() for emb in embeddings]

    def embed_single(self, text: str) -> list[float]:
        self._load_model()
        embedding = self._model.encode(text, convert_to_tensor=False, show_progress_bar=False)
        return embedding.tolist()


class OpenAIEmbedder(EmbeddingProvider):
    """Embedder using OpenAI API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "text-embedding-3-small",
        dimension: int | None = None,
    ) -> None:
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._model = model
        self._dimension = dimension or (1536 if "3-small" in model else 3072)
        self._client = None

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def name(self) -> str:
        return f"openai/{self._model}"

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self._api_key)
            except ImportError:
                raise RuntimeError("openai package not installed")
        return self._client

    async def embed_async(self, texts: list[str]) -> list[list[float]]:
        client = self._get_client()
        response = await client.embeddings.create(
            model=self._model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def embed(self, texts: list[str]) -> list[list[float]]:
        import asyncio
        return asyncio.run(self.embed_async(texts))

    async def embed_single_async(self, text: str) -> list[float]:
        client = self._get_client()
        response = await client.embeddings.create(
            model=self._model,
            input=[text],
        )
        return response.data[0].embedding

    def embed_single(self, text: str) -> list[float]:
        import asyncio
        return asyncio.run(self.embed_single_async(text))


class EmbeddingManager:
    """Manages embedding providers with caching and fallback."""

    def __init__(
        self,
        provider: str = "sentence-transformers",
        model: str = "all-MiniLM-L6-v2",
        dimension: int = 384,
        cache_dir: str | None = None,
        batch_size: int = 32,
    ) -> None:
        self._provider_name = provider
        self._model_name = model
        self._dimension = dimension
        self._batch_size = batch_size
        self._cache_dir = Path(cache_dir) if cache_dir else None
        self._cache: dict[str, list[float]] = {}
        self._provider: EmbeddingProvider | None = None
        self._initialize_provider()

    def _initialize_provider(self) -> None:
        """Initialize the embedding provider."""
        if self._provider_name == "sentence-transformers":
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                try:
                    self._provider = SentenceTransformersEmbedder(self._model_name)
                    if LOGURU_AVAILABLE:
                        logger.info(f"Using sentence-transformers: {self._model_name}")
                    else:
                        logger.info(f"Using sentence-transformers: {self._model_name}")
                except Exception as e:
                    if LOGURU_AVAILABLE:
                        logger.warning(f"Failed to load sentence-transformers: {e}, falling back to hashing")
                    else:
                        logger.warning(f"Failed to load sentence-transformers: {e}, falling back to hashing")
                    self._provider = HashingEmbedder(self._dimension)
            else:
                if LOGURU_AVAILABLE:
                    logger.warning("sentence-transformers not available, using hashing fallback")
                else:
                    logger.warning("sentence-transformers not available, using hashing fallback")
                self._provider = HashingEmbedder(self._dimension)

        elif self._provider_name == "openai":
            try:
                self._provider = OpenAIEmbedder(model=self._model_name, dimension=self._dimension)
                if LOGURU_AVAILABLE:
                    logger.info(f"Using OpenAI embeddings: {self._model_name}")
                else:
                    logger.info(f"Using OpenAI embeddings: {self._model_name}")
            except Exception as e:
                if LOGURU_AVAILABLE:
                    logger.warning(f"Failed to load OpenAI embedder: {e}, falling back to hashing")
                else:
                    logger.warning(f"Failed to load OpenAI embedder: {e}, falling back to hashing")
                self._provider = HashingEmbedder(self._dimension)

        elif self._provider_name == "hashing":
            self._provider = HashingEmbedder(self._dimension)
            if LOGURU_AVAILABLE:
                logger.info("Using hashing embedder (fallback)")
            else:
                logger.info("Using hashing embedder (fallback)")

        else:
            if LOGURU_AVAILABLE:
                logger.warning(f"Unknown provider: {self._provider_name}, using hashing fallback")
            else:
                logger.warning(f"Unknown provider: {self._provider_name}, using hashing fallback")
            self._provider = HashingEmbedder(self._dimension)

        # Ensure dimension matches provider
        if self._provider:
            self._dimension = self._provider.dimension

    @property
    def provider(self) -> EmbeddingProvider:
        return self._provider

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings with caching."""
        if not self._provider:
            self._initialize_provider()

        # Check cache
        uncached = []
        uncached_indices = []
        results = [None] * len(texts)

        for i, text in enumerate(texts):
            cache_key = self._cache_key(text)
            if cache_key in self._cache:
                results[i] = self._cache[cache_key]
            else:
                uncached.append(text)
                uncached_indices.append(i)

        # Generate embeddings for uncached texts
        if uncached:
            new_embeddings = self._provider.embed(uncached)
            for idx, emb in zip(uncached_indices, new_embeddings):
                cache_key = self._cache_key(texts[idx])
                self._cache[cache_key] = emb
                results[idx] = emb

        return results

    def embed_single(self, text: str) -> list[float]:
        """Generate embedding for single text with caching."""
        return self.embed([text])[0]

    def _cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.sha256(f"{self._provider_name}:{self._model_name}:{text}".encode()).hexdigest()

    async def embed_async(self, texts: list[str]) -> list[list[float]]:
        """Async embed (uses sync implementation for now)."""
        import asyncio
        return await asyncio.to_thread(self.embed, texts)

    def clear_cache(self) -> None:
        """Clear embedding cache."""
        self._cache.clear()
        if LOGURU_AVAILABLE:
            logger.debug("Embedding cache cleared")
        else:
            logger.debug("Embedding cache cleared")


# Missing import
from pathlib import Path
import hashlib

__all__ = [
    "EmbeddingProvider",
    "HashingEmbedder",
    "SentenceTransformersEmbedder",
    "OpenAIEmbedder",
    "EmbeddingManager",
]