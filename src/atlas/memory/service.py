"""MemoryService — public API for Atlas OS memory system.

Offline-first design:
    1. Uses local ``sentence-transformers`` embeddings when available.
    2. Falls back to deterministic ``HashEmbedder`` when not installed.
    3. Never sends memory data to cloud services by default.
    4. Stores memories locally with optional disk persistence.

Usage::

    svc = MemoryService()
    svc.remember("The user prefers dark mode.")
    results = svc.recall("What are the user's UI preferences?")
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from atlas.memory.embedder import Embedder, HashEmbedder, create_best_embedder
from atlas.memory.store import MemoryEntry, MemoryResult, MemoryStore

logger = logging.getLogger(__name__)


def default_memory_persist_path(data_dir: str | Path) -> Path:
    """Return the shared memories.json path, falling back to legacy memory.json."""
    base = Path(data_dir)
    base.mkdir(parents=True, exist_ok=True)
    primary = base / "memories.json"
    legacy = base / "memory.json"
    if not primary.exists() and legacy.exists():
        return legacy
    return primary


class MemoryService:
    """High-level memory management service.

    Args:
        embedder:     Custom ``Embedder`` instance.  When ``None`` (default),
                      ``create_best_embedder()`` is called which prefers
                      ``sentence-transformers`` and falls back to ``HashEmbedder``.
        persist_path: Optional path for JSON persistence.  ``None`` = in-memory only.
        model_name:   sentence-transformers model to use when ``embedder`` is ``None``.
                      Ignored if ``embedder`` is provided.
    """

    def __init__(
        self,
        embedder: Embedder | None = None,
        persist_path: str | Path | None = None,
        model_name: str = "all-MiniLM-L6-v2",
    ) -> None:
        if embedder is not None:
            self._embedder: Embedder = embedder
        else:
            self._embedder = create_best_embedder(model_name)

        self._store = MemoryStore(persist_path)
        logger.info(
            "MemoryService ready: embedder=%s, dim=%d, entries=%d",
            self._embedder.name,
            self._embedder.dimension,
            len(self._store),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def embedder_name(self) -> str:
        """Name of the active embedder."""
        return self._embedder.name

    @property
    def embedder_dimension(self) -> int:
        """Dimension of embedding vectors produced by the active embedder."""
        return self._embedder.dimension

    @property
    def entry_count(self) -> int:
        """Number of memories currently stored."""
        return len(self._store)

    def remember(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Store a memory.

        Args:
            text:     The text to remember.
            metadata: Optional arbitrary key/value metadata.
        """
        embedding = self._embedder.embed(text)
        entry = MemoryEntry(
            text=text,
            embedding=embedding,
            metadata=metadata or {},
        )
        self._store.add(entry)
        self._store.save()

    def remember_batch(
        self,
        texts: list[str],
        metadata: list[dict[str, Any]] | None = None,
    ) -> None:
        """Store multiple memories efficiently.

        Args:
            texts:    List of texts to remember.
            metadata: Optional list of metadata dicts (same length as ``texts``).
        """
        if not texts:
            return
        meta_list = metadata or [{} for _ in texts]
        embeddings = self._embedder.embed_batch(texts)
        for text, emb, meta in zip(texts, embeddings, meta_list):
            self._store.add(MemoryEntry(text=text, embedding=emb, metadata=meta))
        self._store.save()

    def recall(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = -1.0,
    ) -> list[MemoryResult]:
        """Retrieve memories similar to a query.

        Args:
            query:     Query text.
            top_k:     Maximum number of results to return.
            threshold: Minimum cosine similarity score (-1.0 = no filter).


        Returns:
            List of ``MemoryResult`` sorted by similarity (highest first).
        """
        query_embedding = self._embedder.embed(query)
        return self._store.search(query_embedding, top_k=top_k, threshold=threshold)

    def clear(self) -> None:
        """Remove all stored memories and save the empty state."""
        self._store.clear()
        self._store.save()

    def list_all(self) -> list[MemoryEntry]:
        """Return all stored memory entries."""
        return self._store.entries

    def delete_by_id(self, memory_id: str) -> bool:
        """Delete a memory by metadata id and persist the change."""
        removed = self._store.delete_by_id(memory_id)
        if removed:
            self._store.save()
        return removed

    def status(self) -> dict[str, Any]:
        """Return memory system status for health checks."""
        return {
            "embedder": self._embedder.name,
            "embedder_dimension": self._embedder.dimension,
            "entry_count": self._store.entry_count if hasattr(self._store, "entry_count") else len(self._store),
            "local_embeddings": not isinstance(self._embedder, HashEmbedder),
            "hash_fallback": isinstance(self._embedder, HashEmbedder),
        }
