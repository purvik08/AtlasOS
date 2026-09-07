"""Simple local vector store for Atlas OS memory.

Keeps memory entries in-process (RAM) with optional disk persistence.
No external vector database required.  Designed for offline-first use.

Persistence is JSON-based so the store survives restarts.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """A single stored memory."""
    text: str
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "embedding": self.embedding,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryEntry":
        return cls(
            text=data["text"],
            embedding=data["embedding"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class MemoryResult:
    """A retrieval result with similarity score."""
    text: str
    score: float            # cosine similarity in [0, 1]
    metadata: dict[str, Any] = field(default_factory=dict)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


class MemoryStore:
    """In-memory vector store with optional JSON persistence.

    Thread-safety: Not thread-safe; designed for single-threaded / asyncio use.
    Call ``save()`` / ``load()`` explicitly for persistence.
    """

    def __init__(self, persist_path: str | Path | None = None) -> None:
        self._entries: list[MemoryEntry] = []
        self._persist_path = Path(persist_path) if persist_path else None

        if self._persist_path and self._persist_path.exists():
            self._load_from_disk()

    @property
    def entries(self) -> list[MemoryEntry]:
        """Return a copy of stored memory entries."""
        return list(self._entries)

    def add(self, entry: MemoryEntry) -> None:
        """Store a memory entry."""
        self._entries.append(entry)
        logger.debug("MemoryStore: added entry (total=%d)", len(self._entries))

    def delete_by_id(self, memory_id: str) -> bool:
        """Remove the first entry whose metadata id matches *memory_id*."""
        remaining = [
            entry
            for entry in self._entries
            if (entry.metadata or {}).get("id") != memory_id
        ]
        removed = len(remaining) != len(self._entries)
        self._entries = remaining
        return removed

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        threshold: float = -1.0,
    ) -> list[MemoryResult]:
        """Return the top-k most similar entries.

        Args:
            query_embedding: Query vector (must match stored embedding dimension).
            top_k:           Maximum number of results.
            threshold:       Minimum cosine similarity score (-1.0 = return all).


        Returns:
            List of ``MemoryResult`` sorted by similarity (highest first).
        """
        if not self._entries:
            return []

        scored: list[tuple[float, MemoryEntry]] = []
        for entry in self._entries:
            if len(entry.embedding) != len(query_embedding):
                continue
            score = _cosine_similarity(query_embedding, entry.embedding)
            if score >= threshold:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            MemoryResult(
                text=entry.text,
                score=score,
                metadata=entry.metadata,
            )
            for score, entry in scored[:top_k]
        ]

    def clear(self) -> None:
        """Remove all stored memories."""
        self._entries.clear()
        logger.info("MemoryStore: cleared all entries")

    def __len__(self) -> int:
        return len(self._entries)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> None:
        """Persist the store to disk (if ``persist_path`` was set)."""
        if self._persist_path is None:
            return
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        data = [entry.to_dict() for entry in self._entries]
        self._persist_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.debug("MemoryStore: saved %d entries to %s", len(data), self._persist_path)

    def _load_from_disk(self) -> None:
        try:
            raw = json.loads(self._persist_path.read_text(encoding="utf-8"))  # type: ignore[union-attr]
            self._entries = [MemoryEntry.from_dict(d) for d in raw]
            logger.info(
                "MemoryStore: loaded %d entries from %s",
                len(self._entries), self._persist_path,
            )
        except Exception as exc:
            logger.warning("MemoryStore: failed to load from disk: %s", exc)
            self._entries = []
