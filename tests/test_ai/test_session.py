"""Tests for ChatSession and SessionManager."""

from __future__ import annotations

import pytest

from atlas.ai.session import ChatSession, SessionManager
from atlas.ai.providers.base import MessageRole


@pytest.fixture
def manager():
    return SessionManager(max_history_messages=10)


# ---------------------------------------------------------------------------
# ChatSession
# ---------------------------------------------------------------------------


def test_session_has_unique_id():
    s1 = ChatSession(provider_name="llama_cpp", model_id="m1")
    s2 = ChatSession(provider_name="llama_cpp", model_id="m1")
    assert s1.session_id != s2.session_id


def test_session_stores_provider_and_model():
    s = ChatSession(provider_name="gemini", model_id="gemini-1.5-flash")
    assert s.provider_name == "gemini"
    assert s.model_id == "gemini-1.5-flash"


def test_session_add_user_message():
    s = ChatSession(provider_name="p", model_id="m")
    msg = s.add_user_message("Hello")
    assert msg.role is MessageRole.USER
    assert msg.content == "Hello"
    assert len(s.history) == 1


def test_session_add_assistant_message():
    s = ChatSession(provider_name="p", model_id="m")
    msg = s.add_assistant_message("Hi there!")
    assert msg.role is MessageRole.ASSISTANT
    assert len(s.history) == 1


def test_session_get_messages_returns_all():
    s = ChatSession(provider_name="p", model_id="m")
    s.add_user_message("u")
    s.add_assistant_message("a")
    msgs = s.get_messages()
    assert len(msgs) == 2


def test_session_system_prompt_prepended():
    s = ChatSession(provider_name="p", model_id="m", system_prompt="Be helpful.")
    msgs = s.get_messages()
    assert msgs[0].role is MessageRole.SYSTEM
    assert msgs[0].content == "Be helpful."


def test_session_metadata_stored():
    s = ChatSession(provider_name="p", model_id="m", metadata={"user": "alice"})
    assert s.metadata["user"] == "alice"


# ---------------------------------------------------------------------------
# SessionManager
# ---------------------------------------------------------------------------


def test_create_returns_session(manager):
    s = manager.create(provider_name="llama_cpp", model_id="q4")
    assert isinstance(s, ChatSession)
    assert manager.count() == 1


def test_get_returns_same_session(manager):
    s = manager.create(provider_name="llama_cpp", model_id="q4")
    retrieved = manager.get(s.session_id)
    assert retrieved is s


def test_get_unknown_raises_key_error(manager):
    with pytest.raises(KeyError, match="not found"):
        manager.get("does-not-exist")


def test_delete_removes_session(manager):
    s = manager.create(provider_name="p", model_id="m")
    manager.delete(s.session_id)
    assert manager.count() == 0


def test_delete_unknown_raises_key_error(manager):
    with pytest.raises(KeyError, match="not found"):
        manager.delete("not-real")


def test_list_all_ordered_by_creation_time(manager):
    ids = []
    for i in range(3):
        s = manager.create(provider_name="p", model_id=f"m{i}")
        ids.append(s.session_id)
    listed = manager.list_all()
    assert [s.session_id for s in listed] == ids


def test_count_zero_initially(manager):
    assert manager.count() == 0


def test_len_matches_count(manager):
    manager.create(provider_name="p", model_id="m")
    manager.create(provider_name="p", model_id="m")
    assert len(manager) == 2


def test_create_with_system_prompt(manager):
    s = manager.create(
        provider_name="llama_cpp",
        model_id="m",
        system_prompt="You are a helpful assistant.",
    )
    msgs = s.get_messages()
    assert msgs[0].role is MessageRole.SYSTEM
