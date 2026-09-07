"""Embedding providers for Atlas OS memory system.

Preferred order (offline-first):
    1. SentenceTransformerEmbedder  — local ML model (sentence-transformers)
    2. HashEmbedder                 — deterministic hash-based fallback (zero deps)

``sentence-transformers`` is intentionally optional and never a mandatory
dependency for basic AtlasOS operation. The HashEmbedder always works.

No cloud embedding services are used by default.
"""

from __future__ import annotations

import hashlib
import logging
import struct
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)

# Dimensionality constants
_HASH_DIM = 128         # HashEmbedder output dimension
_ST_DEFAULT_MODEL = "all-MiniLM-L6-v2"   # ~80 MB, CPU-friendly


class Embedder(ABC):
    """Abstract embedder interface."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Output vector dimension."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable embedder name."""

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Embed ``text`` and return a float vector of length ``self.dimension``."""

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts.  Subclasses may override for efficiency."""
        return [self.embed(t) for t in texts]


class HashEmbedder(Embedder):
    """Deterministic hash-based embedder.

    Produces a 128-dimensional float32 vector from the SHA-256 hash of
    the input text.  This embedder requires **no ML dependencies** and
    is always available.  Similarity is still meaningful for identical or
    near-identical texts but degrades compared to real semantic embeddings.

    This is the guaranteed fallback for offline-first operation.
    """

    @property
    def dimension(self) -> int:
        return _HASH_DIM

    @property
    def name(self) -> str:
        return "HashEmbedder"

    def embed(self, text: str) -> list[float]:
        """Produce a normalised 128-d vector from the text hash."""
        raw = text.strip().lower().encode("utf-8")

        # Generate enough hash bytes by SHA-256-chaining
        # 128 floats × 4 bytes each = 512 bytes → need 16 SHA-256 digests
        digest_chunks: list[bytes] = []
        seed = raw
        for _ in range(16):
            h = hashlib.sha256(seed).digest()
            digest_chunks.append(h)
            seed = h  # chain

        all_bytes = b"".join(digest_chunks)  # 512 bytes
        raw_ints = list(struct.unpack("128i", all_bytes))
        floats = [float(x) / 2147483648.0 for x in raw_ints]

        # L2-normalise so cosine similarity is equivalent to dot product
        magnitude = sum(v * v for v in floats) ** 0.5
        if magnitude > 0.0:
            floats = [v / magnitude for v in floats]
        else:
            floats = [0.0] * _HASH_DIM
        return floats



class SentenceTransformerEmbedder(Embedder):
    """Local sentence-transformers embedder.

    Requires ``sentence-transformers`` to be installed::

        pip install sentence-transformers

    The model is downloaded once to ``~/.cache/huggingface`` (or the
    HF_HOME env var). No internet access is required after the first
    download — fully offline thereafter.

    GPU is NOT required; the default model runs comfortably on CPU /
    Raspberry Pi 5.
    """

    def __init__(self, model_name: str = _ST_DEFAULT_MODEL) -> None:
        self._model_name = model_name
        self._model: Any = None
        self._dim: int = 0
        self._load()

    def _load(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore[import]
            # Load strictly from local cache to prevent network hangs in offline-first environment
            self._model = SentenceTransformer(self._model_name, local_files_only=True)
            probe = self._model.encode([""], convert_to_numpy=True)
            self._dim = int(probe.shape[1])
            logger.info(
                "SentenceTransformerEmbedder loaded: model=%s, dim=%d",
                self._model_name, self._dim,
            )
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is not installed. "
                "Install with: pip install sentence-transformers\n"
                "AtlasOS will fall back to HashEmbedder automatically."
            ) from exc
        except Exception as exc:
            raise RuntimeError(
                f"SentenceTransformer local model '{self._model_name}' not cached or failed to load: {exc}"
            ) from exc

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def name(self) -> str:
        return f"SentenceTransformerEmbedder({self._model_name})"

    def embed(self, text: str) -> list[float]:
        """Embed text using the loaded model."""
        if self._model is None:
            raise RuntimeError("SentenceTransformerEmbedder model not loaded")
        result = self._model.encode([text], convert_to_numpy=True, normalize_embeddings=True)
        return result[0].tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Efficient batch embedding."""
        if self._model is None:
            raise RuntimeError("SentenceTransformerEmbedder model not loaded")
        results = self._model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return [row.tolist() for row in results]


def create_best_embedder(
    model_name: str = _ST_DEFAULT_MODEL,
) -> Embedder:
    """Return the best available embedder.

    Tries ``SentenceTransformerEmbedder`` first; falls back to ``HashEmbedder``
    if ``sentence-transformers`` is not installed or fails to load.

    This is the function ``MemoryService`` uses internally.
    """
    try:
        embedder = SentenceTransformerEmbedder(model_name)
        logger.info("Using local sentence-transformers embedder (%s)", embedder.name)
        return embedder
    except (ImportError, RuntimeError) as exc:
        logger.warning(
            "sentence-transformers unavailable (%s). "
            "Using HashEmbedder fallback. "
            "Install with: pip install sentence-transformers",
            exc,
        )
        return HashEmbedder()
