"""Tests for AIRouter — role-based selection, explicit name, fallback."""

from __future__ import annotations

import pytest

from atlas.ai.providers.base import AIProvider, ProviderRole
from atlas.ai.router import AIRouter, ProviderNotFoundError

# ---------------------------------------------------------------------------
# Minimal test double
# ---------------------------------------------------------------------------


class _FakeProvider(AIProvider):
    def __init__(self, name: str, role: ProviderRole) -> None:
        self._name = name
        self._role = role

    @property
    def name(self) -> str:
        return self._name

    @property
    def role(self) -> ProviderRole:
        return self._role

    @property
    def description(self) -> str:
        return f"Fake {self._name}"

    async def load_model(self, model_id: str) -> None: ...
    async def unload_model(self, model_id: str) -> None: ...
    async def list_models(self): return []
    async def chat(self, messages, model_id, **kwargs): ...  # type: ignore[return]
    async def stream_chat(self, messages, model_id, **kwargs):  # type: ignore[override]
        return
        yield  # noqa: unreachable – makes it an async generator
    async def health(self): ...  # type: ignore[return]


@pytest.fixture
def local():
    return _FakeProvider("llama_cpp", ProviderRole.LOCAL)


@pytest.fixture
def cloud():
    return _FakeProvider("gemini", ProviderRole.CLOUD)


@pytest.fixture
def router(local, cloud):
    r = AIRouter()
    r.register(local)
    r.register(cloud)
    return r


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def test_register_and_get(local):
    r = AIRouter()
    r.register(local)
    assert r.get("llama_cpp") is local


def test_register_duplicate_replaces(local):
    r = AIRouter()
    r.register(local)
    new_local = _FakeProvider("llama_cpp", ProviderRole.LOCAL)
    r.register(new_local)
    assert r.get("llama_cpp") is new_local


def test_unregister(local):
    r = AIRouter()
    r.register(local)
    r.unregister("llama_cpp")
    assert "llama_cpp" not in r.registered_names()


def test_unregister_unknown_is_noop(local):
    r = AIRouter()
    r.unregister("nonexistent")  # must not raise


def test_get_unknown_raises(local):
    r = AIRouter()
    with pytest.raises(ProviderNotFoundError):
        r.get("unknown")


# ---------------------------------------------------------------------------
# Selection — explicit name
# ---------------------------------------------------------------------------


def test_select_by_name(router, local):
    assert router.select(provider_name="llama_cpp") is local


def test_select_by_name_unknown_raises(router):
    with pytest.raises(ProviderNotFoundError):
        router.select(provider_name="not-registered")


# ---------------------------------------------------------------------------
# Selection — role-based
# ---------------------------------------------------------------------------


def test_select_local_role(router, local):
    assert router.select(role=ProviderRole.LOCAL) is local


def test_select_cloud_role(router, cloud):
    assert router.select(role=ProviderRole.CLOUD) is cloud


def test_select_auto_prefers_local(router, local):
    result = router.select(role=ProviderRole.AUTO)
    assert result is local


def test_select_auto_falls_to_cloud_if_no_local(cloud):
    r = AIRouter()
    r.register(cloud)
    result = r.select(role=ProviderRole.AUTO)
    assert result is cloud


def test_select_role_missing_raises():
    r = AIRouter()
    with pytest.raises(ProviderNotFoundError):
        r.select(role=ProviderRole.LOCAL)


# ---------------------------------------------------------------------------
# Default role
# ---------------------------------------------------------------------------


def test_default_role_used_when_no_args(local):
    r = AIRouter(default_role=ProviderRole.LOCAL)
    r.register(local)
    assert r.select() is local


# ---------------------------------------------------------------------------
# select_with_fallback
# ---------------------------------------------------------------------------


def test_select_with_fallback_succeeds_normally(router, local):
    result = router.select_with_fallback(role=ProviderRole.LOCAL)
    assert result is local


def test_select_with_fallback_falls_back_to_first(local, cloud):
    r = AIRouter()
    r.register(local)   # registered first
    r.register(cloud)
    # Requesting cloud-only router but asking for LOCAL with no local provider
    r2 = AIRouter()
    r2.register(cloud)
    result = r2.select_with_fallback(role=ProviderRole.LOCAL)
    assert result is cloud


def test_select_with_fallback_raises_when_empty():
    r = AIRouter()
    with pytest.raises(ProviderNotFoundError):
        r.select_with_fallback(role=ProviderRole.LOCAL)
