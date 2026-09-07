"""Atlas OS memory module.

Offline-first memory with local embeddings.

Preferred embedding order:
    1. SentenceTransformerEmbedder (local ML, optional dep)
    2. HashEmbedder (zero-dep deterministic fallback)

No cloud embedding services are used by default.
"""

from __future__ import annotations

from atlas.memory.embedder import (
    Embedder,
    HashEmbedder,
    SentenceTransformerEmbedder,
    create_best_embedder,
)
from atlas.memory.service import MemoryService
from atlas.memory.store import MemoryEntry, MemoryResult, MemoryStore

__all__ = [
    "MemoryService",
    "Embedder",
    "HashEmbedder",
    "SentenceTransformerEmbedder",
    "create_best_embedder",
    "MemoryStore",
    "MemoryEntry",
    "MemoryResult",
]
