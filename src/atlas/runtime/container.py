"""A minimal, explicit dependency-injection container for Atlas OS.

This container deliberately avoids "magic" auto-wiring based on type hints.
Every binding is registered explicitly, which keeps behaviour predictable and
makes the container easy to reason about and test.

Two kinds of providers are supported:

* **Instance** bindings return the same pre-built object every time.
* **Factory** bindings call a (sync or async) callable to produce a value,
  either once (singleton scope) or on every resolution (transient scope).
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Callable
from enum import Enum
from typing import Any, TypeVar

from atlas.runtime.exceptions import DependencyResolutionError

logger = logging.getLogger(__name__)

T = TypeVar("T")
#: A zero-argument callable producing a value, sync or async. Kept loosely
#: typed on purpose: this container is keyed by arbitrary hashable values and
#: resolves to `Any`, so there is no static type to parameterize `Factory`
#: with at the container level -- callers are responsible for casting the
#: result of `resolve()`/`resolve_async()` to the type they expect.
Factory = Callable[[], Any]

_UNSET = object()


class Scope(str, Enum):
    """Lifetime scope of a container-managed dependency."""

    SINGLETON = "singleton"
    TRANSIENT = "transient"


class _Binding:
    __slots__ = ("factory", "scope", "instance", "is_async")

    def __init__(self, factory: Factory, scope: Scope) -> None:
        self.factory = factory
        self.scope = scope
        self.instance: Any = _UNSET
        self.is_async = inspect.iscoroutinefunction(factory)


class DependencyContainer:
    """Explicit, key-based dependency injection container.

    Keys are typically classes or ``Protocol`` types, but any hashable value
    (including plain strings) may be used.
    """

    def __init__(self) -> None:
        self._bindings: dict[Any, _Binding] = {}
        self._resolving: set[Any] = set()

    def register_instance(self, key: Any, instance: T) -> None:
        """Bind *key* to a pre-constructed *instance* (always singleton)."""

        binding = _Binding(lambda: instance, Scope.SINGLETON)
        binding.instance = instance
        self._bindings[key] = binding

    def register_factory(
        self, key: Any, factory: Factory, *, scope: Scope = Scope.TRANSIENT
    ) -> None:
        """Bind *key* to a factory callable, sync or async.

        Args:
            key: Lookup key, conventionally a type or Protocol.
            factory: Zero-argument callable producing the dependency. May be
                a coroutine function, in which case callers must use
                :meth:`resolve_async`.
            scope: ``SINGLETON`` caches the first produced value; ``TRANSIENT``
                calls the factory on every resolution.
        """

        self._bindings[key] = _Binding(factory, scope)

    def is_registered(self, key: Any) -> bool:
        """Return ``True`` if *key* has a binding registered."""

        return key in self._bindings

    def __contains__(self, key: Any) -> bool:
        """Support `key in container` syntax."""
        return self.is_registered(key)

    def resolve(self, key: Any) -> Any:
        """Resolve *key* to a concrete instance using a synchronous factory.

        Raises:
            DependencyResolutionError: if *key* is unregistered, the bound
                factory is asynchronous, or a circular resolution is detected.
        """

        binding = self._get_binding(key)
        if binding.is_async:
            raise DependencyResolutionError(
                f"{key!r} is bound to an async factory; use resolve_async()."
            )

        if binding.scope is Scope.SINGLETON and binding.instance is not _UNSET:
            return binding.instance

        self._guard_cycle(key)
        try:
            value = binding.factory()
        finally:
            self._resolving.discard(key)

        if binding.scope is Scope.SINGLETON:
            binding.instance = value
        return value

    async def resolve_async(self, key: Any) -> Any:
        """Resolve *key*, awaiting the factory if it is a coroutine function."""

        binding = self._get_binding(key)

        if binding.scope is Scope.SINGLETON and binding.instance is not _UNSET:
            return binding.instance

        self._guard_cycle(key)
        try:
            result = binding.factory()
            value = await result if inspect.isawaitable(result) else result
        finally:
            self._resolving.discard(key)

        if binding.scope is Scope.SINGLETON:
            binding.instance = value
        return value

    def _get_binding(self, key: Any) -> _Binding:
        try:
            return self._bindings[key]
        except KeyError as exc:
            raise DependencyResolutionError(
                f"No binding registered for {key!r}."
            ) from exc

    def _guard_cycle(self, key: Any) -> None:
        if key in self._resolving:
            raise DependencyResolutionError(
                f"Circular dependency detected while resolving {key!r}."
            )
        self._resolving.add(key)

    def clear(self) -> None:
        """Remove all bindings. Primarily useful for test isolation."""

        self._bindings.clear()
        self._resolving.clear()
