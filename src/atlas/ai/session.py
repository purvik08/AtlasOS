"""Chat session management for Atlas OS.

A :class:`ChatSession` represents one conversation thread — it pairs a
:class:`~atlas.ai.history.ConversationHistory` with a chosen provider and
model, and carries enough metadata for the CLI and API to present it
meaningfully.

The :class:`SessionManager` creates, retrieves, lists, and deletes sessions.
It is owned by :class:`~atlas.ai.manager.AIManager` and should not be
instantiated directly.

Sessions are kept in-memory for Phase 5.  Persistence to disk or a database
is deferred to a later phase and won't require changing the public interface.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Iterator

from atlas.ai.history import ConversationHistory
from atlas.ai.providers.base import Message, MessageRole

logger = logging.getLogger(__name__)


class ChatSession:
    """A single conversation thread.

    Attributes
    ----------
    session_id:
        Universally unique identifier (UUID4 string).
    provider_name:
        Name of the assigned :class:`~atlas.ai.providers.base.AIProvider`.
    model_id:
        Model that will be used for inference in this session.
    created_at:
        UTC timestamp of session creation.
    history:
        The conversation history owned by this session.
    metadata:
        Arbitrary key/value pairs (e.g. client info, tags).
    """

    def __init__(
        self,
        provider_name: str,
        model_id: str,
        max_history_messages: int = 50,
        system_prompt: str = "",
        metadata: dict | None = None,
    ) -> None:
        self.session_id: str = str(uuid.uuid4())
        self.provider_name: str = provider_name
        self.model_id: str = model_id
        self.created_at: datetime = datetime.now(timezone.utc)
        self.history: ConversationHistory = ConversationHistory(
            max_messages=max_history_messages,
            session_id=self.session_id,
        )
        self.metadata: dict = metadata or {}

        if system_prompt:
            self.history.set_system_prompt(system_prompt)

        logger.debug(
            "ChatSession %s created: provider=%s, model=%s",
            self.session_id,
            provider_name,
            model_id,
        )

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def add_user_message(self, content: str) -> Message:
        """Append a user-role message and return it."""
        msg = Message(role=MessageRole.USER, content=content)
        self.history.append(msg)
        return msg

    def add_assistant_message(self, content: str) -> Message:
        """Append an assistant-role message and return it."""
        msg = Message(role=MessageRole.ASSISTANT, content=content)
        self.history.append(msg)
        return msg

    def get_messages(self) -> list[Message]:
        """Return all messages in this session, oldest-first."""
        return self.history.get_all()

    def __repr__(self) -> str:
        return (
            f"ChatSession(id={self.session_id!r}, "
            f"provider={self.provider_name!r}, model={self.model_id!r}, "
            f"messages={len(self.history)})"
        )


class SessionManager:
    """Creates, tracks, and destroys chat sessions.

    The manager is *not* a service itself — it is owned by
    :class:`~atlas.ai.manager.AIManager`.  All operations are synchronous
    and O(1) or O(n) with small *n* (user-facing session counts are tiny).
    """

    def __init__(self, max_history_messages: int = 50) -> None:
        self._sessions: dict[str, ChatSession] = {}
        self._max_history_messages = max_history_messages
        logger.debug("SessionManager initialised.")

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(
        self,
        provider_name: str,
        model_id: str,
        system_prompt: str = "",
        metadata: dict | None = None,
    ) -> ChatSession:
        """Create and register a new :class:`ChatSession`.

        Parameters
        ----------
        provider_name:
            Name of the provider that will handle inference.
        model_id:
            Model to use within that provider.
        system_prompt:
            Optional system instruction prepended to every inference call.
        metadata:
            Arbitrary key/value pairs attached to the session.

        Returns
        -------
        ChatSession
            The newly created session.
        """
        session = ChatSession(
            provider_name=provider_name,
            model_id=model_id,
            max_history_messages=self._max_history_messages,
            system_prompt=system_prompt,
            metadata=metadata,
        )
        self._sessions[session.session_id] = session
        logger.info(
            "Session %s created (provider=%s, model=%s).",
            session.session_id,
            provider_name,
            model_id,
        )
        return session

    def get(self, session_id: str) -> ChatSession:
        """Retrieve an existing session by ID.

        Raises
        ------
        KeyError
            If *session_id* is not found.
        """
        try:
            return self._sessions[session_id]
        except KeyError:
            raise KeyError(f"Session '{session_id}' not found.") from None

    def delete(self, session_id: str) -> None:
        """Delete a session and its history.

        Raises
        ------
        KeyError
            If *session_id* is not found.
        """
        if session_id not in self._sessions:
            raise KeyError(f"Session '{session_id}' not found.")
        del self._sessions[session_id]
        logger.info("Session %s deleted.", session_id)

    def list_all(self) -> list[ChatSession]:
        """Return all active sessions, ordered by creation time."""
        return sorted(self._sessions.values(), key=lambda s: s.created_at)

    def count(self) -> int:
        """Return the number of active sessions."""
        return len(self._sessions)

    # ------------------------------------------------------------------
    # Iteration
    # ------------------------------------------------------------------

    def __iter__(self) -> Iterator[ChatSession]:
        return iter(self._sessions.values())

    def __len__(self) -> int:
        return len(self._sessions)

    def __repr__(self) -> str:
        return f"SessionManager(active_sessions={len(self._sessions)})"
