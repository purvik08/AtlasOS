"""Memory system data models for Atlas OS."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass
class Conversation:
    """A conversation containing multiple messages."""

    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Conversation":
        return cls(
            id=data.get("id", str(uuid4())),
            title=data.get("title", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.utcnow(),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Message:
    """A single message within a conversation."""

    id: str = field(default_factory=lambda: str(uuid4()))
    conversation_id: str = ""
    role: str = "user"  # user, assistant, system
    content: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    embedding: list[float] | None = None
    token_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "embedding": self.embedding,
            "token_count": self.token_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Message":
        return cls(
            id=data.get("id", str(uuid4())),
            conversation_id=data.get("conversation_id", ""),
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.utcnow(),
            embedding=data.get("embedding"),
            token_count=data.get("token_count", 0),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Document:
    """A document for RAG ingestion."""

    id: str = field(default_factory=lambda: str(uuid4()))
    content: str = ""
    embedding: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "embedding": self.embedding,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Document":
        return cls(
            id=data.get("id", str(uuid4())),
            content=data.get("content", ""),
            embedding=data.get("embedding", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SearchResult:
    """Result from a semantic search."""

    id: str
    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    conversation_id: str | None = None
    message_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "score": self.score,
            "metadata": self.metadata,
            "conversation_id": self.conversation_id,
            "message_id": self.message_id,
        }


__all__ = [
    "Conversation",
    "Message",
    "Document",
    "SearchResult",
]