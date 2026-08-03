"""Health reporting primitives for Atlas OS.

Defines the vocabulary used across the runtime to describe service and
system health, plus a ``HealthMonitor`` background task that polls the
``ServiceRegistry`` on an interval and keeps an aggregated, cached report
available for the API and dashboard to read without blocking on live checks.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from atlas.runtime.registry import ServiceRegistry

logger = logging.getLogger(__name__)

_STATUS_SEVERITY = {
    "unknown": 0,
    "healthy": 1,
    "degraded": 2,
    "unhealthy": 3,
}


class HealthStatus(str, Enum):
    """Health of a single service or of the aggregate system."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ServiceHealth:
    """Health result for a single service at a point in time."""

    name: str
    status: HealthStatus
    message: str | None = None
    latency_ms: float | None = None
    checked_at: float = field(default_factory=time.time)


@dataclass(frozen=True, slots=True)
class HealthReport:
    """Aggregated health of the whole runtime."""

    status: HealthStatus
    services: tuple[ServiceHealth, ...]
    generated_at: float = field(default_factory=time.time)

    @staticmethod
    def aggregate(services: list[ServiceHealth]) -> HealthReport:
        """Build a report whose overall status is the worst of *services*."""

        if not services:
            return HealthReport(status=HealthStatus.UNKNOWN, services=())

        worst = max(services, key=lambda s: _STATUS_SEVERITY[s.status.value])
        return HealthReport(status=worst.status, services=tuple(services))


HealthReportListener = Callable[[HealthReport], None]


class HealthMonitor:
    """Periodically polls a ``ServiceRegistry`` and caches the result.

    Reading :attr:`latest_report` is synchronous and non-blocking, which is
    what makes it safe to call from a hot HTTP request path (e.g. the
    ``/health`` endpoint) without waiting on live service checks.
    """

    def __init__(
        self, registry: ServiceRegistry, *, interval_seconds: float = 15.0
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive.")
        self._registry = registry
        self._interval = interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._latest = HealthReport(status=HealthStatus.UNKNOWN, services=())
        self._listeners: list[HealthReportListener] = []

    @property
    def latest_report(self) -> HealthReport:
        """The most recently computed health report (cached, non-blocking)."""

        return self._latest

    def add_listener(self, listener: HealthReportListener) -> None:
        """Register a callback invoked with each new ``HealthReport``."""

        self._listeners.append(listener)

    async def start(self) -> None:
        """Begin periodic polling in the background."""

        if self._task is not None:
            return
        # Run one check immediately so a fresh report is available right away
        # instead of waiting a full interval before the first result exists.
        await self._poll_once()
        self._task = asyncio.create_task(self._run(), name="atlas-health-monitor")

    async def stop(self) -> None:
        """Cancel the background polling loop and wait for it to exit."""

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
                await self._poll_once()
        except asyncio.CancelledError:
            raise

    async def _poll_once(self) -> None:
        try:
            results = await self._registry.check_health()
        except Exception:  # noqa: BLE001
            logger.exception("Health monitor polling cycle failed.")
            return
        report = HealthReport.aggregate(results)
        self._latest = report
        for listener in list(self._listeners):
            try:
                listener(report)
            except Exception:  # noqa: BLE001
                logger.exception("Health report listener raised.")
