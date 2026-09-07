"""Unit tests for ChatModel."""

from __future__ import annotations

import sys
import pytest
from PySide6.QtGui import QGuiApplication

from atlas.ui.dashboard.models.chat_model import ChatModel


@pytest.fixture(scope="session")
def qapp():
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv[:1])
    return app


class TestChatModel:
    """Test ChatModel transcript manipulation and streaming tokens."""

    def test_initial_greeting(self, qapp):
        model = ChatModel()
        assert model.rowCount() == 1
        idx = model.index(0, 0)
        assert model.data(idx, model.SenderRole) == "assistant"
        assert len(model.data(idx, model.TextRole)) > 0

    def test_send_message(self, qapp):
        model = ChatModel()
        model.setSession("test-sess-123")
        received = []
        model.messageSent.connect(lambda sid, mdl, txt: received.append((sid, mdl, txt)))

        model.sendMessage("Hello Atlas")
        assert model.rowCount() == 2
        user_idx = model.index(1, 0)
        assert model.data(user_idx, model.SenderRole) == "user"
        assert model.data(user_idx, model.TextRole) == "Hello Atlas"
        assert len(received) == 1
        assert received[0] == ("test-sess-123", "default", "Hello Atlas")

    def test_append_streaming_chunk(self, qapp):
        model = ChatModel()
        model.appendStreamingChunk("First token ")
        assert model.rowCount() == 2
        last_idx = model.index(1, 0)
        assert model.data(last_idx, model.SenderRole) == "assistant"
        assert model.data(last_idx, model.IsStreamingRole) is True

        model.appendStreamingChunk("second token")
        assert model.rowCount() == 2
        assert model.data(last_idx, model.TextRole) == "First token second token"

        model.finishStreaming()
        assert model.data(last_idx, model.IsStreamingRole) is False

    def test_set_session_messages(self, qapp):
        model = ChatModel()
        history = [
            {"role": "user", "content": "What is AtlasOS?"},
            {"role": "assistant", "content": "AtlasOS is an edge AI operating system."},
        ]
        model.setSessionMessages(history)
        assert model.rowCount() == 2
        assert model.data(model.index(0, 0), model.SenderRole) == "user"
        assert model.data(model.index(1, 0), model.SenderRole) == "assistant"

    def test_clear(self, qapp):
        model = ChatModel()
        model.sendMessage("Test 1")
        model.sendMessage("Test 2")
        model.clear()
        assert model.rowCount() == 1
