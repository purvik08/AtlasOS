"""Custom exception hierarchy for the Atlas OS runtime core.

All runtime-related errors inherit from :class:`AtlasRuntimeError` so callers
can catch every runtime failure with a single except clause, while still
being able to catch more specific error types when finer-grained handling
is required.
"""

from __future__ import annotations


class AtlasRuntimeError(Exception):
    """Base class for all runtime-related errors."""


class InvalidStateTransitionError(AtlasRuntimeError):
    """Raised when an illegal runtime state transition is attempted."""

    def __init__(self, current_state: str, target_state: str) -> None:
        self.current_state = current_state
        self.target_state = target_state
        super().__init__(
            f"Cannot transition from '{current_state}' to '{target_state}'."
        )


class ServiceNotFoundError(AtlasRuntimeError):
    """Raised when a requested service is not present in the registry."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Service '{name}' is not registered.")


class ServiceAlreadyRegisteredError(AtlasRuntimeError):
    """Raised when attempting to register a service name that already exists."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Service '{name}' is already registered.")


class CircularDependencyError(AtlasRuntimeError):
    """Raised when a cycle is detected while resolving service start order."""

    def __init__(self, cycle: list[str]) -> None:
        self.cycle = cycle
        super().__init__(
            "Circular dependency detected among services: " + " -> ".join(cycle)
        )


class ServiceStartError(AtlasRuntimeError):
    """Raised when a service fails to start."""

    def __init__(self, name: str, original: Exception) -> None:
        self.name = name
        self.original = original
        super().__init__(f"Service '{name}' failed to start: {original}")


class ServiceStopError(AtlasRuntimeError):
    """Raised when a service fails to stop cleanly."""

    def __init__(self, name: str, original: Exception) -> None:
        self.name = name
        self.original = original
        super().__init__(f"Service '{name}' failed to stop: {original}")


class DependencyResolutionError(AtlasRuntimeError):
    """Raised when the DI container cannot resolve a requested dependency."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
