"""RAGService — Core Retrieval-Augmented Generation service for Atlas OS.

Integrates with Atlas OS Memory subsystem, supporting offline-first document
ingestion, chunking, embeddings, vector search, citations, and prompt augmentation.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from atlas.memory.embedder import Embedder, create_best_embedder
from atlas.rag.document import Document, DocumentChunk, DocumentChunker, IngestionResult, TextExtractor

logger = logging.getLogger(__name__)


@dataclass
class RAGSearchResult:
    """A semantic retrieval result from the RAG knowledge base."""
    chunk_id: str
    doc_id: str
    doc_title: str
    source_path: str
    text: str
    score: float
    chunk_index: int
    total_chunks: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "doc_title": self.doc_title,
            "source_path": self.source_path,
            "text": self.text,
            "score": round(self.score, 4),
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "metadata": self.metadata,
        }


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


class RAGService:
    """High-level Retrieval-Augmented Generation service.

    Args:
        embedder: Custom embedder instance. Defaults to best available local embedder.
        data_dir: Storage directory for persistent document catalog and index.
        chunk_size: Target characters per chunk.
        chunk_overlap: Overlap characters between chunks.
    """

    def __init__(
        self,
        embedder: Embedder | None = None,
        data_dir: str | Path = "./data",
        chunk_size: int = 600,
        chunk_overlap: int = 100,
        memory_service: Any | None = None,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self._embedder = embedder or create_best_embedder()
        self._memory_service = memory_service
        self._chunker = DocumentChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        self._docs_file = self.data_dir / "rag_documents.json"
        self._index_file = self.data_dir / "rag_index.json"

        self._documents: dict[str, Document] = {}
        self._chunks: dict[str, DocumentChunk] = {}
        self._embeddings: dict[str, list[float]] = {}  # chunk_id -> embedding vector

        self._load_persistence()
        logger.info(
            "RAGService ready: embedder=%s (dim=%d), docs=%d, chunks=%d",
            self._embedder.name,
            self._embedder.dimension,
            len(self._documents),
            len(self._chunks),
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_persistence(self) -> None:
        """Load documents and chunk index from disk."""
        if self._docs_file.exists():
            try:
                with open(self._docs_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        doc = Document.from_dict(item)
                        self._documents[doc.doc_id] = doc
            except Exception as exc:
                logger.warning("RAGService: failed to load %s: %s", self._docs_file, exc)

        if self._index_file.exists():
            try:
                with open(self._index_file, "r", encoding="utf-8") as f:
                    items = json.load(f)
                    for item in items:
                        chunk = DocumentChunk.from_dict(item["chunk"])
                        self._chunks[chunk.chunk_id] = chunk
                        self._embeddings[chunk.chunk_id] = item["embedding"]
            except Exception as exc:
                logger.warning("RAGService: failed to load %s: %s", self._index_file, exc)

    def _save_persistence(self) -> None:
        """Save documents and chunk embeddings to disk."""
        try:
            docs_data = [d.to_dict() for d in self._documents.values()]
            with open(self._docs_file, "w", encoding="utf-8") as f:
                json.dump(docs_data, f, indent=2)

            index_data = [
                {"chunk": self._chunks[cid].to_dict(), "embedding": self._embeddings[cid]}
                for cid in self._chunks
                if cid in self._embeddings
            ]
            with open(self._index_file, "w", encoding="utf-8") as f:
                json.dump(index_data, f, indent=2)
        except Exception as exc:
            logger.error("RAGService: error saving persistence: %s", exc)

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest_file(
        self,
        file_path: str | Path,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> IngestionResult:
        """Ingest a local document file (txt, md, json, py, log, etc.)."""
        path = Path(file_path).resolve()
        if not path.exists():
            return IngestionResult(
                success=False,
                doc_id="",
                title="",
                chunk_count=0,
                error=f"File not found: {path}",
            )

        try:
            text, detected_title, mime_type = TextExtractor.extract(path)
            doc_title = title or detected_title
            content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            doc_id = f"doc_{content_hash[:10]}"

            # Remove existing version if re-ingesting same content
            if doc_id in self._documents:
                self.delete_document(doc_id)

            chunks = self._chunker.chunk_text(
                text=text,
                doc_id=doc_id,
                doc_title=doc_title,
                source_path=str(path),
                metadata=metadata,
            )

            # Generate embeddings
            for chunk in chunks:
                emb = self._embedder.embed(chunk.text)
                self._chunks[chunk.chunk_id] = chunk
                self._embeddings[chunk.chunk_id] = emb

            doc = Document(
                doc_id=doc_id,
                title=doc_title,
                source_path=str(path),
                content_hash=content_hash,
                chunk_count=len(chunks),
                created_at=datetime.now().isoformat(),
                file_size_bytes=path.stat().st_size,
                mime_type=mime_type,
                metadata=metadata or {},
            )
            self._documents[doc_id] = doc
            self._save_persistence()

            logger.info("RAGService: ingested %s (%d chunks).", doc_title, len(chunks))
            return IngestionResult(
                success=True,
                doc_id=doc_id,
                title=doc_title,
                chunk_count=len(chunks),
            )
        except Exception as exc:
            logger.exception("RAGService: ingestion failed for %s", path)
            return IngestionResult(
                success=False,
                doc_id="",
                title=title or path.stem,
                chunk_count=0,
                error=str(exc),
            )

    def ingest_text(
        self,
        text: str,
        title: str,
        source: str = "manual",
        metadata: dict[str, Any] | None = None,
    ) -> IngestionResult:
        """Ingest raw text content as a document."""
        clean_text = text.strip()
        if not clean_text:
            return IngestionResult(
                success=False,
                doc_id="",
                title=title,
                chunk_count=0,
                error="Text content is empty.",
            )

        try:
            content_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()
            doc_id = f"doc_{content_hash[:10]}"

            if doc_id in self._documents:
                self.delete_document(doc_id)

            chunks = self._chunker.chunk_text(
                text=clean_text,
                doc_id=doc_id,
                doc_title=title,
                source_path=source,
                metadata=metadata,
            )

            for chunk in chunks:
                emb = self._embedder.embed(chunk.text)
                self._chunks[chunk.chunk_id] = chunk
                self._embeddings[chunk.chunk_id] = emb

            doc = Document(
                doc_id=doc_id,
                title=title,
                source_path=source,
                content_hash=content_hash,
                chunk_count=len(chunks),
                created_at=datetime.now().isoformat(),
                file_size_bytes=len(clean_text.encode("utf-8")),
                mime_type="text/plain",
                metadata=metadata or {},
            )
            self._documents[doc_id] = doc
            self._save_persistence()

            return IngestionResult(
                success=True,
                doc_id=doc_id,
                title=title,
                chunk_count=len(chunks),
            )
        except Exception as exc:
            logger.exception("RAGService: text ingestion failed for %s", title)
            return IngestionResult(
                success=False,
                doc_id="",
                title=title,
                chunk_count=0,
                error=str(exc),
            )

    def ingest_directory(
        self,
        directory_path: str | Path,
        recursive: bool = True,
        extensions: tuple[str, ...] = (".txt", ".md", ".json", ".py", ".log"),
    ) -> list[IngestionResult]:
        """Batch ingest all supported documents from a directory."""
        dir_path = Path(directory_path)
        if not dir_path.is_dir():
            return []

        results: list[IngestionResult] = []
        pattern = "**/*" if recursive else "*"
        for p in dir_path.glob(pattern):
            if p.is_file() and p.suffix.lower() in extensions:
                res = self.ingest_file(p)
                results.append(res)

        return results

    # ------------------------------------------------------------------
    # Retrieval & Search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.0,
    ) -> list[RAGSearchResult]:
        """Search knowledge chunks by semantic similarity to query."""
        clean_query = query.strip()
        if not clean_query:
            return []

        query_emb = self._embedder.embed(clean_query)
        scored: list[tuple[str, float]] = []

        for chunk_id, emb in self._embeddings.items():
            sim = _cosine_similarity(query_emb, emb)
            if sim >= threshold:
                scored.append((chunk_id, sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        top_results = scored[:max(1, top_k)]

        results: list[RAGSearchResult] = []
        for chunk_id, score in top_results:
            chunk = self._chunks.get(chunk_id)
            if chunk is not None:
                results.append(
                    RAGSearchResult(
                        chunk_id=chunk.chunk_id,
                        doc_id=chunk.doc_id,
                        doc_title=chunk.doc_title,
                        source_path=chunk.source_path,
                        text=chunk.text,
                        score=score,
                        chunk_index=chunk.chunk_index,
                        total_chunks=chunk.total_chunks,
                        metadata=chunk.metadata,
                    )
                )

        if self._memory_service is not None:
            try:
                memories = self._memory_service.recall(clean_query, top_k=top_k)
            except Exception as exc:
                logger.debug("RAGService: memory recall skipped: %s", exc)
                memories = []
            for idx, mem in enumerate(memories):
                mem_score = float(getattr(mem, "score", 0.0) or 0.0)
                if mem_score < threshold:
                    continue
                meta = getattr(mem, "metadata", {}) or {}
                mem_id = str(meta.get("id", f"mem-{idx}"))
                results.append(
                    RAGSearchResult(
                        chunk_id=f"memory:{mem_id}",
                        doc_id=mem_id,
                        doc_title="Atlas Memory",
                        source_path="memory",
                        text=getattr(mem, "text", ""),
                        score=mem_score,
                        chunk_index=idx,
                        total_chunks=len(memories),
                        metadata=meta,
                    )
                )
            results.sort(key=lambda r: r.score, reverse=True)
            results = results[:max(1, top_k)]

        return results

    def build_rag_context(
        self,
        query: str,
        top_k: int = 3,
        max_chars: int = 2500,
        threshold: float = 0.05,
    ) -> str:
        """Construct formatted contextual snippets and citations for LLM prompt augmentation."""
        results = self.search(query, top_k=top_k, threshold=threshold)
        if not results:
            return ""

        context_parts: list[str] = [
            "### Relevant Context from Knowledge Base:"
        ]
        total_len = len(context_parts[0])

        for idx, res in enumerate(results, 1):
            source_info = f"Source {idx}: [{res.doc_title}] ({Path(res.source_path).name if res.source_path else 'inline'})"
            chunk_snippet = f"{source_info}\n\"\"\"\n{res.text.strip()}\n\"\"\""
            
            if total_len + len(chunk_snippet) > max_chars and idx > 1:
                break

            context_parts.append(chunk_snippet)
            total_len += len(chunk_snippet)

        return "\n\n".join(context_parts)

    # ------------------------------------------------------------------
    # Document Management
    # ------------------------------------------------------------------

    def list_documents(self) -> list[Document]:
        """Return all registered documents sorted by creation date."""
        return sorted(self._documents.values(), key=lambda d: d.created_at, reverse=True)

    def get_document(self, doc_id: str) -> Document | None:
        """Get document metadata by ID."""
        return self._documents.get(doc_id)

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document and all its indexed chunks."""
        if doc_id not in self._documents:
            return False

        del self._documents[doc_id]

        # Prune associated chunks
        chunks_to_delete = [
            cid for cid, chunk in self._chunks.items()
            if chunk.doc_id == doc_id
        ]
        for cid in chunks_to_delete:
            self._chunks.pop(cid, None)
            self._embeddings.pop(cid, None)

        self._save_persistence()
        logger.info("RAGService: deleted document %s (%d chunks removed).", doc_id, len(chunks_to_delete))
        return True

    def clear(self) -> None:
        """Delete all indexed documents and embeddings."""
        self._documents.clear()
        self._chunks.clear()
        self._embeddings.clear()
        self._save_persistence()
        logger.info("RAGService: cleared all documents and index.")
