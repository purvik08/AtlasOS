"""Conversation history management for Atlas OS AI sessions.

Each active :class:`~atlas.ai.session.ChatSession` owns one
:class:`ConversationHistory` instance.  History is stored in insertion order
as an ordered list of :class:`~atlas.ai.providers.base.Message` objects.

Design choices
--------------
* History is kept purely in-memory for Phase 5.  Persistence (SQLite or JSON
  file) is a later concern and won't require an interface change.
* ``truncate_to_fit`` uses a simple word-count approximation for token budget
  until a real tokeniser is wired in (Phase 6 / llama-cpp-python).
* The class is intentionally *not* async — history access is always in-memory
  and synchronous; callers add the ``await`` wrapping if needed.
"""

from __future__ import annotations

import logging
from collections import deque

from atlas.ai.providers.base import Message, MessageRole

logger = logging.getLogger(__name__)

# Rough words-per-token approximation used when no tokeniser is available.
_WORDS_PER_TOKEN = 0.75


class ConversationHistory:
    """Ordered, bounded message history for a single chat session.

    Parameters
    ----------
    max_messages:
        Hard cap on the number of messages retained.  When exceeded the
        oldest non-system messages are dropped first.  ``0`` means no cap.
    session_id:
        Owning session identifier; used only for logging.
    """

    def __init__(self, max_messages: int = 50, session_id: str = "") -> None:
        self._max_messages = max_messages
        self._session_id = session_id
        self._messages: deque[Message] = deque()
        logger.debug(
            "ConversationHistory created for session=%s, max_messages=%d",
            session_id,
            max_messages,
        )

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def append(self, message: Message) -> None:
        """Add *message* to the end of the history.

        If the history has reached ``max_messages``, the oldest *non-system*
        message is evicted before appending, preserving the system prompt
        (if any) at position 0.
        """
        if self._max_messages > 0 and len(self._messages) >= self._max_messages:
            self._evict_oldest_non_system()

        self._messages.append(message)
        logger.debug(
            "History[%s] appended %s message (total=%d)",
            self._session_id,
            message.role.value,
            len(self._messages),
        )

    def clear(self) -> None:
        """Remove all messages from history."""
        self._messages.clear()
        logger.debug("History[%s] cleared.", self._session_id)

    def set_system_prompt(self, content: str) -> None:
        """Replace (or insert) a system-role message at position 0.

        If the first message is already a system message it is replaced;
        otherwise a new system message is prepended.
        """
        system_msg = Message(role=MessageRole.SYSTEM, content=content)
        messages = list(self._messages)

        if messages and messages[0].role is MessageRole.SYSTEM:
            messages[0] = system_msg
        else:
            messages.insert(0, system_msg)

        self._messages = deque(messages)
        logger.debug("History[%s] system prompt updated.", self._session_id)

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------

    def get_all(self) -> list[Message]:
        """Return a shallow copy of all messages in chronological order."""
        return list(self._messages)

    def get_last_n(self, n: int) -> list[Message]:
        """Return the *n* most recent messages."""
        return list(self._messages)[-n:]

    def __len__(self) -> int:
        return len(self._messages)

    # ------------------------------------------------------------------
    # Token budget management
    # ------------------------------------------------------------------

    def truncate_to_fit(self, max_tokens: int) -> list[Message]:
        """Return a token-budget-aware slice of history for use in a prompt.

        Starts from the most recent message and works backwards, keeping as
        many messages as fit within *max_tokens*.  System messages are always
        included at position 0 regardless of budget.

        The original history is **not mutated** — this is a read-only view
        for building the prompt payload.

        Parameters
        ----------
        max_tokens:
            Approximate token budget for the returned slice.

        Returns
        -------
        list[Message]
            Messages ordered oldest-first, ready to send to a provider.
        """
        messages = list(self._messages)
        if not messages:
            return []

        # Separate system message.
        system: list[Message] = []
        rest: list[Message] = []
        for msg in messages:
            if msg.role is MessageRole.SYSTEM:
                system.append(msg)
            else:
                rest.append(msg)

        system_tokens = sum(self._estimate_tokens(m) for m in system)
        budget = max_tokens - system_tokens
        if budget <= 0:
            return system

        selected: list[Message] = []
        used = 0
        for msg in reversed(rest):
            t = self._estimate_tokens(msg)
            if used + t > budget:
                break
            selected.append(msg)
            used += t

        selected.reverse()
        result = system + selected
        logger.debug(
            "History[%s] truncate_to_fit: kept %d/%d messages (~%d tokens).",
            self._session_id,
            len(result),
            len(messages),
            used + system_tokens,
        )
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _estimate_tokens(msg: Message) -> int:
        """Rough word-count-based token estimate."""
        words = len(msg.content.split())
        return max(1, int(words / _WORDS_PER_TOKEN))

    def _evict_oldest_non_system(self) -> None:
        """Remove the oldest non-system message to make room."""
        messages = list(self._messages)
        for i, msg in enumerate(messages):
            if msg.role is not MessageRole.SYSTEM:
                del messages[i]
                self._messages = deque(messages)
                logger.debug(
                    "History[%s] evicted oldest %s message.",
                    self._session_id,
                    msg.role.value,
                )
                return
        # All messages are system messages; evict the very first.
        if messages:
            del messages[0]
            self._messages = deque(messages)

    def __repr__(self) -> str:
        return (
            f"ConversationHistory(session={self._session_id!r}, "
            f"messages={len(self._messages)}, max={self._max_messages})"
        )
