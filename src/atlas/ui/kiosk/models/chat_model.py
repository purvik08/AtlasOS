"""Chat conversation model for the Atlas OS touch kiosk.

Behaviour
---------
* If an ``AIManager`` instance is passed at construction (via ``kiosk/main.py``
  when a model is loaded), ``sendMessage`` dispatches inference to a
  ``QThread`` worker so the Qt main thread — and therefore the UI — never
  blocks.  Token chunks are streamed back via a ``Signal`` and appended to the
  last assistant message in real-time.

* If *no* ``AIManager`` is provided (standalone kiosk demo, no GGUF on disk),
  the model falls back to the original mock replies so the UI still works.

The docstring in the original file says:
  "swap in this file only"
That contract is preserved: QML screens bind to the same roles and slots.

Roles (unchanged — QML bindings require no edits):
  SenderRole, TextRole, TimestampRole
"""

from __future__ import annotations

import asyncio
import datetime
import logging
import random
from typing import Any

from PySide6.QtCore import (
    QAbstractListModel,
    QModelIndex,
    QObject,
    QThread,
    Qt,
    QTimer,
    Signal,
    Slot,
)

logger = logging.getLogger(__name__)

_MOCK_REPLIES = [
    "Sure -- I can help with that. Which loaded model would you like to use?",
    "Running that now. It should only take a moment on-device.",
    "Here's a summary based on what I have loaded locally.",
    "I don't have network access, but I can work with what's cached.",
    "Done. Let me know if you'd like me to adjust anything.",
]


def _now_hhmm() -> str:
    return datetime.datetime.now().strftime("%H:%M")


# ---------------------------------------------------------------------------
# Background worker — runs the async AIManager.stream_chat in its own thread
# ---------------------------------------------------------------------------

class _InferenceWorker(QObject):
    """Runs inside a QThread; bridges async llama.cpp streaming to Qt signals.

    Signals
    -------
    tokenReady(str):
        Emitted for each text chunk produced by the model.
    finished():
        Emitted when the full response is complete (or on error).
    error(str):
        Emitted with a human-readable message if inference fails.
    """

    tokenReady = Signal(str)
    finished = Signal()
    error = Signal(str)

    def __init__(
        self,
        ai_manager: Any,          # atlas.ai.AIManager
        session_id: str,
        user_text: str,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._manager = ai_manager
        self._session_id = session_id
        self._user_text = user_text

    @Slot()
    def run(self) -> None:
        """Entry point called by QThread.started signal."""
        try:
            asyncio.run(self._stream())
        except Exception as exc:
            logger.exception("InferenceWorker: unexpected error: %s", exc)
            self.error.emit(str(exc))
        finally:
            self.finished.emit()

    async def _stream(self) -> None:
        try:
            async for chunk in self._manager.stream_chat(
                self._session_id, self._user_text
            ):
                self.tokenReady.emit(chunk)
        except Exception as exc:
            logger.error("InferenceWorker: stream_chat error: %s", exc)
            self.error.emit(str(exc))


# ---------------------------------------------------------------------------
# ChatModel
# ---------------------------------------------------------------------------

class ChatModel(QAbstractListModel):
    """A conversation transcript: alternating user/assistant messages.

    Parameters
    ----------
    ai_manager:
        An initialised ``atlas.ai.AIManager`` instance with at least one
        model loaded, or ``None`` to run in mock mode.
    session_id:
        The ``ChatSession.session_id`` to use for all messages.  Ignored in
        mock mode.
    parent:
        Standard Qt parent.
    """

    SenderRole = Qt.ItemDataRole.UserRole + 1
    TextRole = Qt.ItemDataRole.UserRole + 2
    TimestampRole = Qt.ItemDataRole.UserRole + 3

    assistantStartedTyping = Signal()
    assistantFinishedTyping = Signal()

    def __init__(
        self,
        parent: QObject | None = None,
        ai_manager: Any | None = None,
        session_id: str = "",
    ) -> None:
        super().__init__(parent)
        self._ai_manager = ai_manager
        self._session_id = session_id
        self._messages: list[dict[str, Any]] = [
            {
                "sender": "assistant",
                "text": (
                    "Atlas OS is online. Ask me anything — everything runs "
                    "locally on this device."
                ),
                "timestamp": _now_hhmm(),
            }
        ]

        # Tracks the QThread that is currently running inference so we can
        # check whether one is already in flight.
        self._active_thread: QThread | None = None

        # --- Mock-mode fallback ---
        self._reply_timer = QTimer(self)
        self._reply_timer.setSingleShot(True)
        self._reply_timer.timeout.connect(self._emit_mock_reply)

    # ------------------------------------------------------------------
    # QAbstractListModel interface
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _append(self, sender: str, text: str) -> None:
        row = len(self._messages)
        self.beginInsertRows(QModelIndex(), row, row)
        self._messages.append({"sender": sender, "text": text, "timestamp": _now_hhmm()})
        self.endInsertRows()

    def _append_empty_assistant(self) -> int:
        """Add an empty assistant row and return its row index."""
        row = len(self._messages)
        self.beginInsertRows(QModelIndex(), row, row)
        self._messages.append({"sender": "assistant", "text": "", "timestamp": _now_hhmm()})
        self.endInsertRows()
        return row

    def _append_token(self, row: int, token: str) -> None:
        """Append *token* to the message at *row* and emit dataChanged."""
        self._messages[row]["text"] += token
        idx = self.index(row, 0)
        self.dataChanged.emit(idx, idx, [self.TextRole])

    # ------------------------------------------------------------------
    # Public slot — called from QML: chatModel.sendMessage(text)
    # ------------------------------------------------------------------

    @Slot(str)
    def sendMessage(self, text: str) -> None:
        """Append a user message and dispatch inference (or mock reply)."""
        text = text.strip()
        if not text:
            return

        # Prevent sending while a previous inference is still running.
        if self._active_thread is not None and self._active_thread.isRunning():
            logger.debug("ChatModel: ignoring sendMessage — inference in flight.")
            return

        self._append("user", text)
        self.assistantStartedTyping.emit()

        if self._ai_manager is not None and self._session_id:
            self._dispatch_inference(text)
        else:
            # No AI manager available — fall back to mock replies.
            self._reply_timer.start(random.randint(700, 1600))

    # ------------------------------------------------------------------
    # Real inference path (QThread worker)
    # ------------------------------------------------------------------

    def _dispatch_inference(self, user_text: str) -> None:
        """Spin up a QThread to run async streaming inference."""
        # Reserve the assistant row before the thread starts so tokens land
        # in the right place even if the first chunk arrives immediately.
        assistant_row = self._append_empty_assistant()

        worker = _InferenceWorker(
            ai_manager=self._ai_manager,
            session_id=self._session_id,
            user_text=user_text,
        )
        thread = QThread(self)
        worker.moveToThread(thread)

        # Wire signals before starting.
        thread.started.connect(worker.run)
        worker.tokenReady.connect(lambda tok: self._append_token(assistant_row, tok))
        worker.error.connect(lambda msg: self._on_inference_error(assistant_row, msg))
        worker.finished.connect(self._on_inference_finished)
        worker.finished.connect(thread.quit)
        # Clean up the thread and worker objects once done.
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(lambda: setattr(self, "_active_thread", None))

        self._active_thread = thread
        thread.start()
        logger.debug("ChatModel: inference thread started (session=%s).", self._session_id)

    @Slot()
    def _on_inference_finished(self) -> None:
        self.assistantFinishedTyping.emit()
        logger.debug("ChatModel: inference complete.")

    @Slot(str)
    def _on_inference_error(self, row: int, message: str) -> None:
        # Replace the empty placeholder with an error notice.
        self._messages[row]["text"] = (
            f"[Error] Could not get a response from the model: {message}\n"
            "Check that a model is loaded with 'atlas models load <name>'."
        )
        idx = self.index(row, 0)
        self.dataChanged.emit(idx, idx, [self.TextRole])
        self.assistantFinishedTyping.emit()
        logger.error("ChatModel: inference error — %s", message)

    # ------------------------------------------------------------------
    # Mock fallback path
    # ------------------------------------------------------------------

    @Slot()
    def _emit_mock_reply(self) -> None:
        self._append("assistant", random.choice(_MOCK_REPLIES))
        self.assistantFinishedTyping.emit()
