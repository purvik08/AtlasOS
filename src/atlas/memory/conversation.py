"""Conversation management for Atlas OS memory system."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

# Optional import for loguru
try:
    from loguru import logger
    LOGURU_AVAILABLE = True
except ImportError:
    LOGURU_AVAILABLE = False
    import logging
    logger = logging.getLogger(__name__)

from .models import Conversation, Message, SearchResult
from .store import LanceDBStore
from .embeddings import EmbeddingManager
from .search import SemanticSearch


class ConversationManager:
    """Manages conversations, messages, and context windows."""

    def __init__(
        self,
        store: LanceDBStore,
        embedding_manager: EmbeddingManager,
        search: SemanticSearch,
        max_context_tokens: int = 4000,
        auto_embed: bool = True,
    ) -> None:
        self._store = store
        self._embedding_manager = embedding_manager
        self._search = search
        self._max_context_tokens = max_context_tokens
        self._auto_embed = auto_embed

    async def create_conversation(
        self,
        title: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(
            title=title or f"Conversation {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            metadata=metadata or {},
        )

        success = await self._store.create_conversation(conversation)
        if not success:
            raise RuntimeError("Failed to create conversation")

        if LOGURU_AVAILABLE:
            logger.info(f"Created conversation: {conversation.id}")
        else:
            logger.info(f"Created conversation: {conversation.id}")

        return conversation

    async def get_conversation(self, conversation_id: str) -> Conversation | None:
        """Get a conversation by ID."""
        data = await self._store.get_conversation(conversation_id)
        if not data:
            return None
        return Conversation.from_dict(data)

    async def list_conversations(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Conversation]:
        """List conversations."""
        data_list = await self._store.list_conversations(limit, offset)
        return [Conversation.from_dict(data) for data in data_list]

    async def update_conversation(self, conversation: Conversation) -> bool:
        """Update a conversation."""
        conversation.updated_at = datetime.utcnow()
        return await self._store.update_conversation(conversation)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all its messages."""
        return await self._store.delete_conversation(conversation_id)

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        """Add a message to a conversation."""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation not found: {conversation_id}")

        # Estimate token count (rough approximation: 1 token ≈ 4 chars)
        token_count = len(content) // 4

        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            token_count=token_count,
            metadata=metadata or {},
        )

        # Generate embedding if enabled
        if self._auto_embed:
            embedding = self._embedding_manager.embed_single(content)
            message.embedding = embedding

        success = await self._store.add_message(message)
        if not success:
            raise RuntimeError("Failed to add message")

        # Update conversation timestamp
        conversation.updated_at = datetime.utcnow()
        await self._store.update_conversation(conversation)

        if LOGURU_AVAILABLE:
            logger.debug(f"Added message to conversation {conversation_id}: {role}")
        else:
            logger.debug(f"Added message to conversation {conversation_id}: {role}")

        return message

    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Message]:
        """Get messages for a conversation."""
        data_list = await self._store.get_messages(conversation_id, limit, offset)
        return [Message.from_dict(data) for data in data_list]

    async def get_conversation_context(
        self,
        conversation_id: str,
        max_tokens: int | None = None,
    ) -> list[Message]:
        """Get conversation messages within token budget (most recent first)."""
        max_tokens = max_tokens or self._max_context_tokens
        messages = await self.get_messages(conversation_id, limit=1000)

        # Sort by timestamp (oldest first for context building)
        messages.sort(key=lambda m: m.timestamp)

        # Build context within token budget
        context = []
        total_tokens = 0

        for message in reversed(messages):  # Start from most recent
            if total_tokens + message.token_count > max_tokens:
                break
            context.insert(0, message)  # Prepend to maintain chronological order
            total_tokens += message.token_count

        return context

    async def search_conversation(
        self,
        conversation_id: str,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        """Search within a specific conversation."""
        results = await self._search.search_messages(
            query=query,
            conversation_id=conversation_id,
            top_k=top_k,
            min_score=min_score,
        )

        return [
            SearchResult(
                id=r["id"],
                content=r["content"],
                score=r.get("hybrid_score", r.get("rerank_score", 0)),
                metadata=r.get("metadata", {}),
                conversation_id=r.get("conversation_id"),
                message_id=r.get("id"),
            )
            for r in results
        ]

    async def export_conversation(
        self,
        conversation_id: str,
        format: str = "json",
    ) -> str | None:
        """Export conversation to JSON or Markdown."""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return None

        messages = await self.get_messages(conversation_id, limit=10000)
        messages.sort(key=lambda m: m.timestamp)

        if format == "json":
            data = {
                "conversation": conversation.to_dict(),
                "messages": [m.to_dict() for m in messages],
            }
            return json.dumps(data, indent=2)

        elif format == "md":
            lines = [
                f"# {conversation.title}",
                f"**ID:** {conversation.id}",
                f"**Created:** {conversation.created_at.isoformat()}",
                f"**Updated:** {conversation.updated_at.isoformat()}",
                "",
            ]

            for msg in messages:
                role_label = {
                    "user": "**You**",
                    "assistant": "**Assistant**",
                    "system": "**System**",
                }.get(msg.role, msg.role.capitalize())

                lines.append(f"## {role_label} ({msg.timestamp.isoformat()})")
                lines.append(msg.content)
                lines.append("")

            return "\n".join(lines)

        return None

    async def import_conversation(
        self,
        json_data: str,
    ) -> Conversation:
        """Import conversation from JSON."""
        data = json.loads(json_data)

        conv_data = data.get("conversation", {})
        messages_data = data.get("messages", [])

        conversation = Conversation.from_dict(conv_data)
        await self._store.create_conversation(conversation)

        for msg_data in messages_data:
            msg = Message.from_dict(msg_data)
            # Re-embed if needed
            if self._auto_embed and not msg.embedding:
                msg.embedding = self._embedding_manager.embed_single(msg.content)
            await self._store.add_message(msg)

        return conversation


__all__ = ["ConversationManager"]