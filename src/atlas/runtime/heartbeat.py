"""Heartbeat service for Atlas OS.

Emits a periodic "I'm alive" signal that other subsystems (health endpoint,
dashboard, future MQTT presence topic) can observe. Kept intentionally
separate from ``HealthMonitor``: a heartbeat only proves the event loop is
responsive, while health checks assess whether individual services are
functioning correctly.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

HeartbeatListener = Callable[["Heartbeat"], None]


@dataclass(frozen=True, slots=True)
class Heartbeat:
    """A single heartbeat event."""

    sequence: int
    emitted_at: float


class HeartbeatService:
    """Emits a heartbeat on a fixed interval via a background asyncio task."""

    def __init__(self, *, interval_seconds: float = 5.0) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive.")
        self._interval = interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._sequence = 0
        self._last_beat: Heartbeat | None = None
        self._listeners: list[HeartbeatListener] = []

    @property
    def last_beat(self) -> Heartbeat | None:
        """The most recent heartbeat, or ``None`` before the first tick."""

        return self._last_beat

    def seconds_since_last_beat(self) -> float | None:
        """Seconds since the last heartbeat, or ``None`` if never started."""

        if self._last_beat is None:
            return None
        return time.time() - self._last_beat.emitted_at

    def add_listener(self, listener: HeartbeatListener) -> None:
        """Register a callback invoked on every heartbeat tick."""

        self._listeners.append(listener)

    async def start(self) -> None:
        """Begin emitting heartbeats in the background."""

        if self._task is not None:
            return
        self._task = asyncio.create_task(self._run(), name="atlas-heartbeat")

    async def stop(self) -> None:
        """Stop emitting heartbeats and wait for the task to exit."""

        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _run(self) -> None:
        try:
            while True:
                await asyncio.sleep(self._interval)
                self._sequence += 1
                beat = Heartbeat(sequence=self._sequence, emitted_at=time.time())
                self._last_beat = beat
                logger.debug("Heartbeat #%d", beat.sequence)
                for listener in list(self._listeners):
                    try:
                        listener(beat)
                    except Exception:  # noqa: BLE001
                        logger.exception("Heartbeat listener raised.")
        except asyncio.CancelledError:
            raise
