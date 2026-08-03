"""Lifecycle management for Atlas OS.

The ``LifecycleManager`` owns the runtime's state machine. It validates
transitions against the legal-transition table in :mod:`atlas.runtime.state`,
notifies subscribers of state changes, and runs ordered startup/shutdown
hooks independent of any specific service implementation.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from atlas.runtime.exceptions import InvalidStateTransitionError
from atlas.runtime.state import (
    RuntimeState,
    RuntimeStateSnapshot,
    is_transition_allowed,
)

logger = logging.getLogger(__name__)

LifecycleHook = Callable[[], Awaitable[None]]
StateListener = Callable[[RuntimeStateSnapshot, RuntimeStateSnapshot], None]

_DEFAULT_HOOK_PRIORITY = 100


@dataclass(order=True, slots=True)
class _PrioritizedHook:
    priority: int
    sequence: int
    hook: LifecycleHook = field(compare=False)
    name: str = field(compare=False)


class LifecycleManager:
    """Owns runtime state and orchestrates startup/shutdown hooks.

    Hooks run in ascending priority order (lower number first). Hooks with
    equal priority run in registration order. Startup hooks run before the
    runtime declares itself ``RUNNING``; shutdown hooks run after services
    have been stopped, during the ``STOPPING`` phase.
    """

    def __init__(self) -> None:
        self._state = RuntimeStateSnapshot(state=RuntimeState.UNINITIALIZED)
        self._lock = asyncio.Lock()
        self._listeners: list[StateListener] = []
        self._startup_hooks: list[_PrioritizedHook] = []
        self._shutdown_hooks: list[_PrioritizedHook] = []
        self._hook_sequence = 0

    @property
    def state(self) -> RuntimeState:
        """The current runtime state."""

        return self._state.state

    @property
    def snapshot(self) -> RuntimeStateSnapshot:
        """An immutable snapshot of the current state and its age."""

        return self._state

    def add_listener(self, listener: StateListener) -> None:
        """Register a callback invoked synchronously on every state change."""

        self._listeners.append(listener)

    def remove_listener(self, listener: StateListener) -> None:
        """Unregister a previously added state-change listener."""

        if listener in self._listeners:
            self._listeners.remove(listener)

    def register_startup_hook(
        self, hook: LifecycleHook, *, name: str, priority: int = _DEFAULT_HOOK_PRIORITY
    ) -> None:
        """Register a coroutine to run during startup, before ``RUNNING``."""

        self._startup_hooks.append(
            _PrioritizedHook(priority, self._next_sequence(), hook, name)
        )

    def register_shutdown_hook(
        self, hook: LifecycleHook, *, name: str, priority: int = _DEFAULT_HOOK_PRIORITY
    ) -> None:
        """Register a coroutine to run during shutdown, after services stop."""

        self._shutdown_hooks.append(
            _PrioritizedHook(priority, self._next_sequence(), hook, name)
        )

    def _next_sequence(self) -> int:
        self._hook_sequence += 1
        return self._hook_sequence

    async def transition_to(
        self, target: RuntimeState, *, reason: str | None = None
    ) -> None:
        """Move the runtime to *target* state, validating legality first.

        Raises:
            InvalidStateTransitionError: if the transition is not permitted
                from the current state.
        """

        async with self._lock:
            current = self._state.state
            if not is_transition_allowed(current, target):
                raise InvalidStateTransitionError(current.value, target.value)

            previous_snapshot = self._state
            new_snapshot = RuntimeStateSnapshot(state=target, reason=reason)
            self._state = new_snapshot
            logger.info(
                "Runtime state transition: %s -> %s%s",
                current.value,
                target.value,
                f" ({reason})" if reason else "",
            )

        for listener in list(self._listeners):
            try:
                listener(previous_snapshot, new_snapshot)
            except (
                Exception
            ):  # noqa: BLE001 - listener failures must not break lifecycle
                logger.exception("State listener raised an exception.")

    async def run_startup_hooks(self) -> None:
        """Execute all registered startup hooks in priority order."""

        for prioritized in sorted(self._startup_hooks):
            logger.debug(
                "Running startup hook '%s' (priority=%d).",
                prioritized.name,
                prioritized.priority,
            )
            await prioritized.hook()

    async def run_shutdown_hooks(self) -> None:
        """Execute all registered shutdown hooks in priority order.

        Shutdown hooks run best-effort: a failure in one hook is logged but
        does not prevent subsequent hooks from running, since shutdown must
        always make forward progress.
        """

        errors: list[tuple[str, Exception]] = []
        for prioritized in sorted(self._shutdown_hooks):
            try:
                await prioritized.hook()
            except Exception as exc:  # noqa: BLE001
                logger.exception("Shutdown hook '%s' failed.", prioritized.name)
                errors.append((prioritized.name, exc))
        if errors:
            logger.warning(
                "%d shutdown hook(s) failed: %s",
                len(errors),
                ", ".join(name for name, _ in errors),
            )
