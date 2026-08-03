import pytest

from atlas.runtime.container import DependencyContainer, Scope
from atlas.runtime.exceptions import DependencyResolutionError


def test_register_instance_returns_same_object():
    container = DependencyContainer()
    sentinel = object()
    container.register_instance("thing", sentinel)

    assert container.resolve("thing") is sentinel


def test_instance_binding_may_be_none():
    container = DependencyContainer()
    container.register_instance("thing", None)

    assert container.resolve("thing") is None


def test_singleton_factory_called_once():
    container = DependencyContainer()
    calls = []

    def factory():
        calls.append(1)
        return object()

    container.register_factory("svc", factory, scope=Scope.SINGLETON)

    first = container.resolve("svc")
    second = container.resolve("svc")

    assert first is second
    assert len(calls) == 1


def test_transient_factory_called_every_time():
    container = DependencyContainer()
    calls = []

    def factory():
        calls.append(1)
        return object()

    container.register_factory("svc", factory, scope=Scope.TRANSIENT)

    first = container.resolve("svc")
    second = container.resolve("svc")

    assert first is not second
    assert len(calls) == 2


def test_unregistered_key_raises():
    container = DependencyContainer()
    with pytest.raises(DependencyResolutionError):
        container.resolve("missing")


def test_sync_resolve_rejects_async_factory():
    container = DependencyContainer()

    async def factory():
        return object()

    container.register_factory("svc", factory)

    with pytest.raises(DependencyResolutionError):
        container.resolve("svc")


async def test_resolve_async_awaits_coroutine_factory():
    container = DependencyContainer()

    async def factory():
        return "value"

    container.register_factory("svc", factory)

    assert await container.resolve_async("svc") == "value"


async def test_resolve_async_supports_sync_factories_too():
    container = DependencyContainer()
    container.register_factory("svc", lambda: "sync-value")

    assert await container.resolve_async("svc") == "sync-value"


def test_circular_dependency_detected():
    container = DependencyContainer()

    def factory_a():
        return container.resolve("b")

    def factory_b():
        return container.resolve("a")

    container.register_factory("a", factory_a)
    container.register_factory("b", factory_b)

    with pytest.raises(DependencyResolutionError):
        container.resolve("a")


def test_clear_removes_bindings():
    container = DependencyContainer()
    container.register_instance("thing", object())
    container.clear()

    assert not container.is_registered("thing")
