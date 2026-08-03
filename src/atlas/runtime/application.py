"""The top-level Atlas OS application object.

``AtlasApplication`` is the composition root: it owns the dependency
container, service registry, lifecycle manager, health monitor, heartbeat,
and background task manager, and sequences them through startup and
graceful shutdown. This is the class instantiated by ``atlas start`` (once
the CLI module exists) and by the FastAPI app factory in the API module.
"""

from __future__ import annotations

import asyncio
import logging
import time

from atlas.config.settings import AtlasConfig
from atlas.runtime.container import DependencyContainer
from atlas.runtime.health import HealthMonitor
from atlas.runtime.heartbeat import HeartbeatService
from atlas.runtime.lifecycle import LifecycleManager
from atlas.runtime.registry import IService, ServiceRegistry
from atlas.runtime.signals import ShutdownSignalHandler
from atlas.runtime.state import RuntimeState
from atlas.runtime.tasks import BackgroundTaskManager

logger = logging.getLogger(__name__)


class AtlasApplication:
    """Composition root and orchestrator for the Atlas OS runtime.

    Typical usage::

        app = AtlasApplication(config)
        await app.start()
        ...
        await app.stop()

    Or, as an async context manager::

        async with AtlasApplication(config) as app:
            ...

    Or, for a long-running process that should shut down gracefully on
    SIGINT/SIGTERM::

        app = AtlasApplication(config)
        await app.run_forever()
    """

    def __init__(self, config: AtlasConfig) -> None:
        self._config = config
        self._container = DependencyContainer()
        self._registry = ServiceRegistry()
        self._lifecycle = LifecycleManager()
        self._health_monitor = HealthMonitor(
            self._registry, interval_seconds=config.health_check_interval_seconds
        )
        self._heartbeat = HeartbeatService(
            interval_seconds=config.heartbeat_interval_seconds
        )
        self._tasks = BackgroundTaskManager()
        self._signal_handler = ShutdownSignalHandler(self._on_shutdown_signal)
        self._started_at: float | None = None
        self._stopped_event = asyncio.Event()
        self._stopped_event.set()

    # -- Public accessors ----------------------------------------------

    @property
    def config(self) -> AtlasConfig:
        """The configuration this application was constructed with."""

        return self._config

    @property
    def state(self) -> RuntimeState:
        """The current runtime lifecycle state."""

        return self._lifecycle.state

    @property
    def container(self) -> DependencyContainer:
        """The application-wide dependency injection container."""

        return self._container

    @property
    def registry(self) -> ServiceRegistry:
        """The registry of lifecycle-managed services."""

        return self._registry

    @property
    def health_monitor(self) -> HealthMonitor:
        """The background health-polling monitor."""

        return self._health_monitor

    @property
    def heartbeat(self) -> HeartbeatService:
        """The heartbeat emitter."""

        return self._heartbeat

    @property
    def tasks(self) -> BackgroundTaskManager:
        """The supervised background task manager."""

        return self._tasks

    @property
    def uptime_seconds(self) -> float:
        """Seconds since :meth:`start` completed, or ``0`` if not running."""

        if self._started_at is None:
            return 0.0
        return time.monotonic() - self._started_at

    def register_service(self, service: IService) -> None:
        """Register a lifecycle-managed service with the runtime.

        Convenience passthrough to ``self.registry.register``. Must be
        called before :meth:`start`.
        """

        self._registry.register(service)

    # -- Lifecycle -------------------------------------------------------

    async def start(self) -> None:
        """Bring the runtime up: init -> starting -> running.

        Only legal from ``UNINITIALIZED`` or ``STOPPED``; raises
        ``InvalidStateTransitionError`` if called while already starting or
        running.
        """

        await self._lifecycle.transition_to(RuntimeState.INITIALIZING)
        await self._lifecycle.run_startup_hooks()

        await self._lifecycle.transition_to(RuntimeState.STARTING)
        try:
            await self._registry.start_all()
            await self._health_monitor.start()
            await self._heartbeat.start()
        except Exception:
            logger.exception("Startup failed; transitioning to ERROR.")
            await self._lifecycle.transition_to(
                RuntimeState.ERROR, reason="startup failure"
            )
            raise

        self._started_at = time.monotonic()
        self._stopped_event.clear()
        await self._lifecycle.transition_to(RuntimeState.RUNNING)
        logger.info(
            "Atlas OS runtime is RUNNING (app=%s, env=%s).",
            self._config.app_name,
            self._config.environment,
        )

    async def stop(self) -> None:
        """Bring the runtime down: stopping -> stopped, best-effort.

        Always attempts every teardown step even if earlier ones fail, so
        shutdown reliably makes forward progress instead of getting stuck.
        Safe to call more than once or on an already-stopped runtime.
        """

        if self.state in (RuntimeState.STOPPED, RuntimeState.UNINITIALIZED):
            return

        await self._lifecycle.transition_to(
            RuntimeState.STOPPING, reason="shutdown requested"
        )

        await self._heartbeat.stop()
        await self._health_monitor.stop()
        await self._tasks.shutdown(
            timeout_seconds=self._config.graceful_shutdown_timeout_seconds
        )
        await self._registry.stop_all()
        await self._lifecycle.run_shutdown_hooks()

        self._started_at = None
        await self._lifecycle.transition_to(RuntimeState.STOPPED)
        self._stopped_event.set()
        logger.info("Atlas OS runtime is STOPPED.")

    async def run_forever(self) -> None:
        """Start the runtime and block until a shutdown signal is received.

        Installs SIGINT/SIGTERM handlers, calls :meth:`start`, then waits
        until :meth:`stop` has completed before returning. This is the entry
        point used by ``atlas start`` and by Docker/systemd deployments.
        """

        self._signal_handler.install()
        await self.start()
        await self._stopped_event.wait()

    async def _on_shutdown_signal(self) -> None:
        await self.stop()

    async def __aenter__(self) -> AtlasApplication:
        await self.start()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.stop()
