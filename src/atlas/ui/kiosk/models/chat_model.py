"""Mock chat conversation model for the Atlas OS touch kiosk prototype.

Stands in for the real chat transcript that will stream token-by-token from
the Local API's WebSocket once the Local LLM and Local API modules exist.
"""

from __future__ import annotations

import datetime
import random
from typing import Any

from PySide6.QtCore import (
    QAbstractListModel,
    QModelIndex,
    QObject,
    Qt,
    QTimer,
    Signal,
    Slot,
)

_MOCK_REPLIES = [
    "Sure -- I can help with that. Which loaded model would you like to use?",
    "Running that now. It should only take a moment on-device.",
    "Here's a summary based on what I have loaded locally.",
    "I don't have network access, but I can work with what's cached.",
    "Done. Let me know if you'd like me to adjust anything.",
]


class ChatModel(QAbstractListModel):
    """A conversation transcript: alternating user/assistant messages."""

    SenderRole = Qt.ItemDataRole.UserRole + 1
    TextRole = Qt.ItemDataRole.UserRole + 2
    TimestampRole = Qt.ItemDataRole.UserRole + 3

    assistantStartedTyping = Signal()
    assistantFinishedTyping = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._messages: list[dict[str, Any]] = [
            {
                "sender": "assistant",
                "text": "Atlas OS is online. Ask me anything -- everything runs "
                "locally on this device.",
                "timestamp": _now_hhmm(),
            }
        ]
        self._reply_timer = QTimer(self)
        self._reply_timer.setSingleShot(True)
        self._reply_timer.timeout.connect(self._emit_assistant_reply)

    def roleNames(self) -> dict[int, bytes]:
        return {
            self.SenderRole: b"sender",
            self.TextRole: b"text",
            self.TimestampRole: b"timestamp",
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._messages)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._messages)):
            return None
        message = self._messages[index.row()]
        if role == self.SenderRole:
            return message["sender"]
        if role == self.TextRole:
            return message["text"]
        if role == self.TimestampRole:
            return message["timestamp"]
        return None

    def _append(self, sender: str, text: str) -> None:
        row = len(self._messages)
        self.beginInsertRows(QModelIndex(), row, row)
        self._messages.append({"sender": sender, "text": text, "timestamp": _now_hhmm()})
        self.endInsertRows()

    @Slot(str)
    def sendMessage(self, text: str) -> None:
        """Append a user message and schedule a mock assistant reply."""

        text = text.strip()
        if not text:
            return
        self._append("user", text)
        self.assistantStartedTyping.emit()
        self._reply_timer.start(random.randint(700, 1600))

    def _emit_assistant_reply(self) -> None:
        self._append("assistant", random.choice(_MOCK_REPLIES))
        self.assistantFinishedTyping.emit()


def _now_hhmm() -> str:
    return datetime.datetime.now().strftime("%H:%M")
