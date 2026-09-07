"""Prompt template and message formatting manager for Atlas OS.

The :class:`PromptManager` decouples prompt construction and template
rendering from individual providers.
"""

from __future__ import annotations

import logging
from typing import Any

from atlas.ai.providers.base import Message, MessageRole

logger = logging.getLogger(__name__)


_DEFAULT_SYSTEM_PROMPT = (
    "You are Atlas OS, an offline-first AI operating system."
)


class PromptManager:
    """Manages prompt construction, system instructions, and templates.

    Parameters
    ----------
    default_system_prompt:
        Default system instruction used when none is provided.
    """

    def __init__(self, default_system_prompt: str = _DEFAULT_SYSTEM_PROMPT) -> None:
        self._default_system_prompt = default_system_prompt
        self._templates: dict[str, str] = {
            "qa": "Context:\n{context}\n\nQuestion: {question}\nAnswer:",
            "summarize": "Summarize the following text concisely:\n\n{text}",
        }
        logger.debug("PromptManager initialised.")

    def format_messages(
        self,
        messages: list[Message],
        system_prompt: str = "",
    ) -> list[Message]:
        """Ensure a system prompt exists at index 0 of the message list.

        Parameters
        ----------
        messages:
            Chronological list of conversation turns.
        system_prompt:
            Custom system instruction.  If empty, uses default.

        Returns
        -------
        list[Message]
            New list of messages with system prompt at index 0.
        """
        sys_content = system_prompt or self._default_system_prompt
        result = list(messages)

        if not result or result[0].role is not MessageRole.SYSTEM:
            result.insert(0, Message(role=MessageRole.SYSTEM, content=sys_content))
        else:
            if system_prompt:
                result[0] = Message(role=MessageRole.SYSTEM, content=system_prompt)

        return result

    def render_template(self, template_name: str, **kwargs: Any) -> str:
        """Render a pre-registered prompt template with variables."""
        if template_name not in self._templates:
            available = list(self._templates.keys())
            raise KeyError(
                f"Prompt template '{template_name}' not found. "
                f"Registered: {available}"
            )
        return self._templates[template_name].format(**kwargs)

    def register_template(self, name: str, template: str) -> None:
        """Register or overwrite a prompt template string."""
        self._templates[name] = template
        logger.debug("PromptManager: registered template '%s'.", name)

    def __repr__(self) -> str:
        return f"PromptManager(templates={list(self._templates.keys())!r})"
