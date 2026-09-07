"""Chat conversation model for Atlas OS Dashboard.

Provides real conversation transcript management with live streaming response
assembly, model selection, role separation, and session synchronization.
"""

from __future__ import annotations

import datetime
from typing import Any

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QModelIndex,
    QObject,
    Qt,
    Signal,
    Slot,
)


def _now_hhmm() -> str:
    return datetime.datetime.now().strftime("%H:%M")


class ChatModel(QAbstractListModel):
    """Real conversation transcript: alternating user/assistant messages."""

    SenderRole = Qt.ItemDataRole.UserRole + 1
    TextRole = Qt.ItemDataRole.UserRole + 2
    TimestampRole = Qt.ItemDataRole.UserRole + 3
    IsStreamingRole = Qt.ItemDataRole.UserRole + 4

    # Signals
    assistantStartedTyping = Signal()
    assistantFinishedTyping = Signal()
    messageSent = Signal(str, str, str)  # session_id, model_id, text
    selectedModelChanged = Signal(str)
    errorOccurred = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._messages: list[dict[str, Any]] = [
            {
                "sender": "assistant",
                "text": "Atlas OS AI Assistant ready. Everything runs locally on device.",
                "timestamp": _now_hhmm(),
                "is_streaming": False,
            }
        ]
        self._current_session_id: str = ""
        self._selected_model: str = "default"

    def roleNames(self) -> dict[int, bytes]:
        return {
            self.SenderRole: b"sender",
            self.TextRole: b"text",
            self.TimestampRole: b"timestamp",
            self.IsStreamingRole: b"isStreaming",
        }

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        if parent is None:
            parent = QModelIndex()
        return 0 if parent.isValid() else len(self._messages)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._messages)):
            return None
        msg = self._messages[index.row()]
        if role == self.SenderRole:
            return msg["sender"]
        if role == self.TextRole:
            return msg["text"]
        if role == self.TimestampRole:
            return msg["timestamp"]
        if role == self.IsStreamingRole:
            return msg.get("is_streaming", False)
        return None

    @Property(str, notify=selectedModelChanged)
    def selectedModel(self) -> str:
        return self._selected_model

    @Slot(str)
    def setSelectedModel(self, model: str) -> None:
        if self._selected_model != model:
            self._selected_model = model
            self.selectedModelChanged.emit(model)

    def _append(self, sender: str, text: str, is_streaming: bool = False) -> None:
        row = len(self._messages)
        self.beginInsertRows(QModelIndex(), row, row)
        self._messages.append({
            "sender": sender,
            "text": text,
            "timestamp": _now_hhmm(),
            "is_streaming": is_streaming,
        })
        self.endInsertRows()

    @Slot(str)
    def setSession(self, session_id: str) -> None:
        self._current_session_id = session_id

    @Slot(str)
    def sendMessage(self, text: str) -> None:
        """Append user message and emit signal with selected model to trigger real inference."""
        clean_text = text.strip()
        if not clean_text:
            return
        self._append("user", clean_text)
        self.assistantStartedTyping.emit()
        self.messageSent.emit(self._current_session_id, self._selected_model, clean_text)

    @Slot(str, str)
    def sendMessageWithModel(self, text: str, model_id: str) -> None:
        """Send message using an explicitly specified model."""
        clean_text = text.strip()
        if not clean_text:
            return
        if model_id:
            self._selected_model = model_id
            self.selectedModelChanged.emit(model_id)
        self._append("user", clean_text)
        self.assistantStartedTyping.emit()
        self.messageSent.emit(self._current_session_id, self._selected_model, clean_text)

    @Slot(str)
    def appendAssistantMessage(self, text: str) -> None:
        """Append complete assistant response."""
        self._append("assistant", text)
        self.assistantFinishedTyping.emit()

    @Slot(str)
    def appendStreamingChunk(self, chunk: str) -> None:
        """Append real-time token to streaming response."""
        if (
            self._messages
            and self._messages[-1]["sender"] == "assistant"
            and self._messages[-1].get("is_streaming")
        ):
            row = len(self._messages) - 1
            self._messages[row]["text"] += chunk
            idx = self.index(row, 0)
            self.dataChanged.emit(idx, idx, [self.TextRole])
        else:
            self._append("assistant", chunk, is_streaming=True)
            self.assistantStartedTyping.emit()

    @Slot()
    def finishStreaming(self) -> None:
        """Mark stream complete."""
        if self._messages and self._messages[-1].get("is_streaming"):
            row = len(self._messages) - 1
            self._messages[row]["is_streaming"] = False
            idx = self.index(row, 0)
            self.dataChanged.emit(idx, idx, [self.IsStreamingRole])
        self.assistantFinishedTyping.emit()

    @Slot(list)
    def setSessionMessages(self, messages: list[dict[str, Any]]) -> None:
        """Replace transcript with loaded session history."""
        self.beginResetModel()
        self._messages = []
        for m in messages:
            role = m.get("role", "assistant")
            content = m.get("content", "")
            self._messages.append({
                "sender": "user" if role == "user" else "assistant",
                "text": content,
                "timestamp": _now_hhmm(),
                "is_streaming": False,
            })
        if not self._messages:
            self._messages.append({
                "sender": "assistant",
                "text": "Session ready. Ask anything.",
                "timestamp": _now_hhmm(),
                "is_streaming": False,
            })
        self.endResetModel()

    @Slot()
    def clear(self) -> None:
        """Clear conversation transcript."""
        self.beginResetModel()
        self._messages = [
            {
                "sender": "assistant",
                "text": "Conversation cleared.",
                "timestamp": _now_hhmm(),
                "is_streaming": False,
            }
        ]
        self.endResetModel()