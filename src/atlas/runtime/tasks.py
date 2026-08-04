"""Supervised background task management for Atlas OS.

Provides a single place where the runtime spawns and tracks ``asyncio``
tasks that should live for the lifetime of the application (e.g. queue
consumers, watchdogs). Tasks can optionally be restarted automatically on
failure with exponential backoff, so a transient error in a background
worker doesn't silently kill it forever.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

TaskFactory = Callable[[], Awaitable[None]]


class RestartPolicy(str, Enum):
    """When a supervised task should be restarted after it exits."""

    NEVER = "never"
    ON_FAILURE = "on_failure"
    ALWAYS = "always"


@dataclass(slots=True)
class _Supervised:
    name: str
    factory: TaskFactory
    restart_policy: RestartPolicy
    max_restarts: int
    task: asyncio.Task[None] | None = None
    restart_count: int = 0


class BackgroundTaskManager:
    """Spawns, supervises, and gracefully tears down background tasks."""

    def __init__(
        self, *, base_backoff_seconds: float = 1.0, max_backoff_seconds: float = 30.0
    ) -> None:
        self._base_backoff = base_backoff_seconds
        self._max_backoff = max_backoff_seconds
        self._tasks: dict[str, _Supervised] = {}
        self._shutting_down = False

    def spawn(
        self,
        name: str,
        factory: TaskFactory,
        *,
        restart_policy: RestartPolicy = RestartPolicy.ON_FAILURE,
        max_restarts: int = 5,
    ) -> None:
        """Start a supervised background task.

        Args:
            name: Unique task name, used for logging and later lookup.
            factory: Zero-argument coroutine function that runs the task
                body. Called again on each restart, so it must be safe to
                invoke more than once.
            restart_policy: Whether to restart the task if it exits.
            max_restarts: Restart ceiling to prevent infinite crash loops.
        """

        if name in self._tasks:
            raise ValueError(f"A background task named '{name}' already exists.")

        supervised = _Supervised(
            name=name,
            factory=factory,
            restart_policy=restart_policy,
            max_restarts=max_restarts,
        )
        self._tasks[name] = supervised
        supervised.task = asyncio.create_task(
            self._run_supervised(supervised), name=f"atlas-task-{name}"
        )

    async def _run_supervised(self, supervised: _Supervised) -> None:
        while True:
            exited_cleanly = True
            error: Exception | None = None
            try:
                await supervised.factory()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                exited_cleanly = False
                error = exc
                logger.exception(
                    "Background task '%s' raised an exception.", supervised.name
                )

            if self._shutting_down:
                return

            should_restart = (
                supervised.restart_policy is RestartPolicy.ALWAYS
                or (
                    supervised.restart_policy is RestartPolicy.ON_FAILURE
                    and not exited_cleanly
                )
            )
            if (
                not should_restart
                or supervised.restart_count >= supervised.max_restarts
            ):
                if not exited_cleanly and error is not None:
                    logger.error(
                        "Background task '%s' will not be restarted "
                        "(policy=%s, restarts=%d).",
                        supervised.name,
                        supervised.restart_policy.value,
                        supervised.restart_count,
                    )
                return

            supervised.restart_count += 1
            backoff = min(
                self._base_backoff * (2 ** (supervised.restart_count - 1)),
                self._max_backoff,
            )
            logger.warning(
                "Restarting background task '%s' in %.2fs (attempt %d/%d).",
                supervised.name,
                backoff,
                supervised.restart_count,
                supervised.max_restarts,
            )
            await asyncio.sleep(backoff)

    def is_running(self, name: str) -> bool:
        """Return ``True`` if the named task exists and has not finished."""

        supervised = self._tasks.get(name)
        return (
            supervised is not None
            and supervised.task is not None
            and not supervised.task.done()
        )

    async def cancel(self, name: str, *, timeout_seconds: float = 10.0) -> None:
        """Cancel a single named task and wait for it to finish."""

        supervised = self._tasks.pop(name, None)
        if supervised is None or supervised.task is None:
            return
        await self._cancel_task(supervised.task, timeout_seconds=timeout_seconds)

    async def shutdown(self, *, timeout_seconds: float = 10.0) -> None:
        """Cancel every supervised task and prevent further restarts."""

        self._shutting_down = True
        tasks = [s.task for s in self._tasks.values() if s.task is not None]
        try:
            await asyncio.gather(
                *(self._cancel_task(t, timeout_seconds=timeout_seconds) for t in tasks),
                return_exceptions=True,
            )
        finally:
            self._tasks.clear()
            self._shutting_down = False

    @staticmethod
    async def _cancel_task(task: asyncio.Task[None], *, timeout_seconds: float) -> None:
        if task.done():
            return
        task.cancel()
        try:
            await asyncio.wait_for(task, timeout=timeout_seconds)
        except (asyncio.CancelledError, TimeoutError):
            pass