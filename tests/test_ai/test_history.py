"""Tests for ConversationHistory."""

from __future__ import annotations

from atlas.ai.history import ConversationHistory
from atlas.ai.providers.base import Message, MessageRole


def _user(text: str) -> Message:
    return Message(role=MessageRole.USER, content=text)


def _assistant(text: str) -> Message:
    return Message(role=MessageRole.ASSISTANT, content=text)


def _system(text: str) -> Message:
    return Message(role=MessageRole.SYSTEM, content=text)


# ---------------------------------------------------------------------------
# Basic append / get
# ---------------------------------------------------------------------------


def test_empty_history():
    h = ConversationHistory()
    assert len(h) == 0
    assert h.get_all() == []


def test_append_and_retrieve():
    h = ConversationHistory()
    m = _user("hello")
    h.append(m)
    assert len(h) == 1
    assert h.get_all()[0] is m


def test_multiple_appends_maintain_order():
    h = ConversationHistory()
    messages = [_user("a"), _assistant("b"), _user("c")]
    for msg in messages:
        h.append(msg)
    assert h.get_all() == messages


def test_clear_removes_all():
    h = ConversationHistory()
    h.append(_user("hello"))
    h.clear()
    assert len(h) == 0


def test_get_last_n():
    h = ConversationHistory()
    for i in range(5):
        h.append(_user(str(i)))
    last = h.get_last_n(3)
    assert [m.content for m in last] == ["2", "3", "4"]


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------


def test_set_system_prompt_prepends():
    h = ConversationHistory()
    h.append(_user("question"))
    h.set_system_prompt("You are Atlas.")
    msgs = h.get_all()
    assert msgs[0].role is MessageRole.SYSTEM
    assert msgs[0].content == "You are Atlas."


def test_set_system_prompt_replaces_existing():
    h = ConversationHistory()
    h.set_system_prompt("Old prompt")
    h.set_system_prompt("New prompt")
    msgs = h.get_all()
    system_msgs = [m for m in msgs if m.role is MessageRole.SYSTEM]
    assert len(system_msgs) == 1
    assert system_msgs[0].content == "New prompt"


# ---------------------------------------------------------------------------
# max_messages eviction
# ---------------------------------------------------------------------------


def test_eviction_keeps_max_messages():
    h = ConversationHistory(max_messages=3)
    for i in range(5):
        h.append(_user(str(i)))
    assert len(h) == 3


def test_eviction_drops_oldest_non_system_first():
    h = ConversationHistory(max_messages=3)
    h.set_system_prompt("System")  # index 0 — must survive
    h.append(_user("u1"))
    h.append(_user("u2"))
    # Next append should evict u1, not the system prompt.
    h.append(_user("u3"))
    msgs = h.get_all()
    assert msgs[0].role is MessageRole.SYSTEM
    assert any(m.content == "u3" for m in msgs)
    assert not any(m.content == "u1" for m in msgs)


# ---------------------------------------------------------------------------
# truncate_to_fit
# ---------------------------------------------------------------------------


def test_truncate_to_fit_returns_all_if_within_budget():
    h = ConversationHistory()
    h.append(_user("hi"))
    h.append(_assistant("hello"))
    result = h.truncate_to_fit(max_tokens=1000)
    assert len(result) == 2


def test_truncate_to_fit_keeps_system_always():
    h = ConversationHistory()
    h.set_system_prompt("You are Atlas.")
    for _i in range(20):
        h.append(_user("word " * 100))  # large messages to blow budget
    result = h.truncate_to_fit(max_tokens=10)
    assert result[0].role is MessageRole.SYSTEM


def test_truncate_to_fit_empty_history():
    h = ConversationHistory()
    assert h.truncate_to_fit(max_tokens=100) == []


def test_truncate_to_fit_most_recent_kept():
    h = ConversationHistory()
    for i in range(10):
        h.append(_user(f"message {i}"))
    # Budget for ~3 messages worth.
    result = h.truncate_to_fit(max_tokens=10)
    last_content = result[-1].content
    assert last_content == "message 9"
