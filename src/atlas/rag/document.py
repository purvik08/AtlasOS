"""Document models, extractors, and chunking strategies for Atlas OS RAG."""

from __future__ import annotations

import hashlib
import json
import logging
import mimetypes
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """A semantic chunk of an ingested document."""
    chunk_id: str
    doc_id: str
    doc_title: str
    source_path: str
    text: str
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
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocumentChunk:
        return cls(
            chunk_id=data["chunk_id"],
            doc_id=data["doc_id"],
            doc_title=data.get("doc_title", ""),
            source_path=data.get("source_path", ""),
            text=data["text"],
            chunk_index=data.get("chunk_index", 0),
            total_chunks=data.get("total_chunks", 1),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Document:
    """A source document ingested into the knowledge base."""
    doc_id: str
    title: str
    source_path: str
    content_hash: str
    chunk_count: int
    created_at: str
    file_size_bytes: int = 0
    mime_type: str = "text/plain"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "source_path": self.source_path,
            "content_hash": self.content_hash,
            "chunk_count": self.chunk_count,
            "created_at": self.created_at,
            "file_size_bytes": self.file_size_bytes,
            "mime_type": self.mime_type,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Document:
        return cls(
            doc_id=data["doc_id"],
            title=data["title"],
            source_path=data.get("source_path", ""),
            content_hash=data["content_hash"],
            chunk_count=data.get("chunk_count", 0),
            created_at=data.get("created_at", datetime.now().isoformat()),
            file_size_bytes=data.get("file_size_bytes", 0),
            mime_type=data.get("mime_type", "text/plain"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class IngestionResult:
    """Result of a document ingestion operation."""
    success: bool
    doc_id: str
    title: str
    chunk_count: int
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "doc_id": self.doc_id,
            "title": self.title,
            "chunk_count": self.chunk_count,
            "error": self.error,
        }


class TextExtractor:
    """Extracts clean UTF-8 text from various file formats."""

    @staticmethod
    def extract(file_path: Path | str) -> tuple[str, str, str]:
        """Extract text content, guessed title, and mime type.
        
        Returns:
            tuple: (clean_text, title, mime_type)
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        mime, _ = mimetypes.guess_type(str(path))
        mime_type = mime or "text/plain"
        title = path.stem.replace("-", " ").replace("_", " ").title()

        suffix = path.suffix.lower()
        if suffix in (".txt", ".md", ".markdown", ".rst", ".log", ".yaml", ".yml", ".py", ".sh", ".c", ".cpp", ".h", ".js", ".ts", ".html", ".css"):
            text = path.read_text(encoding="utf-8", errors="replace")
        elif suffix == ".json":
            try:
                data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
                text = json.dumps(data, indent=2)
            except Exception:
                text = path.read_text(encoding="utf-8", errors="replace")
        elif suffix == ".csv":
            text = path.read_text(encoding="utf-8", errors="replace")
        else:
            # Fallback text reading
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception as exc:
                raise ValueError(f"Unsupported file format for text extraction: {suffix}") from exc

        return text.strip(), title, mime_type


class DocumentChunker:
    """Splits raw text into overlapping chunks suitable for embeddings and LLM context."""

    def __init__(
        self,
        chunk_size: int = 600,
        chunk_overlap: int = 100,
    ) -> None:
        self.chunk_size = max(100, chunk_size)
        self.chunk_overlap = max(0, min(chunk_overlap, self.chunk_size // 2))

    def chunk_text(
        self,
        text: str,
        doc_id: str,
        doc_title: str = "",
        source_path: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> list[DocumentChunk]:
        """Split text into chunks with overlap while preserving paragraphs where possible."""
        clean_text = text.strip()
        if not clean_text:
            return []

        # Split into paragraph blocks first
        paragraphs = re.split(r"\n\s*\n", clean_text)
        chunks: list[str] = []
        current_chunk: list[str] = []
        current_len = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            para_len = len(para)

            if current_len + para_len <= self.chunk_size:
                current_chunk.append(para)
                current_len += para_len + 2
            else:
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                
                # If paragraph itself is larger than chunk_size, split by sentences/characters
                if para_len > self.chunk_size:
                    start = 0
                    while start < para_len:
                        end = start + self.chunk_size
                        chunks.append(para[start:end])
                        start += self.chunk_size - self.chunk_overlap
                    current_chunk = []
                    current_len = 0
                else:
                    current_chunk = [para]
                    current_len = para_len

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        if not chunks and clean_text:
            chunks = [clean_text]

        total = len(chunks)
        doc_chunks: list[DocumentChunk] = []
        base_meta = metadata or {}

        for idx, chunk_str in enumerate(chunks):
            chunk_hash = hashlib.sha256(f"{doc_id}_{idx}_{chunk_str[:50]}".encode()).hexdigest()[:12]
            chunk_id = f"{doc_id}-chunk-{idx}-{chunk_hash}"
            doc_chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    doc_title=doc_title,
                    source_path=source_path,
                    text=chunk_str,
                    chunk_index=idx,
                    total_chunks=total,
                    metadata={**base_meta, "chunk_index": idx, "total_chunks": total},
                )
            )

        return doc_chunks
