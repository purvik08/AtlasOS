"""Service registry for Atlas OS.

The registry tracks all long-lived, lifecycle-managed services (voice
subsystem, MQTT broker client, model manager, etc.). Unlike the generic
``DependencyContainer``, every entry here must implement ``IService`` and
participate in ordered startup/shutdown.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from atlas.runtime.exceptions import (
    CircularDependencyError,
    ServiceAlreadyRegisteredError,
    ServiceNotFoundError,
    ServiceStartError,
    ServiceStopError,
)
from atlas.runtime.health import HealthStatus, ServiceHealth

logger = logging.getLogger(__name__)


class IService(ABC):
    """Contract every lifecycle-managed Atlas service must implement."""

    #: Names of other registered services that must be started before this
    #: one. Override in subclasses; defaults to no dependencies.
    dependencies: tuple[str, ...] = ()

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique, stable identifier for this service within the registry."""

    @abstractmethod
    async def start(self) -> None:
        """Perform startup work (open connections, spawn workers, etc.)."""

    @abstractmethod
    async def stop(self) -> None:
        """Perform shutdown work. Must be safe to call even after a failed start."""

    async def health_check(self) -> ServiceHealth:
        """Report current health. Default implementation reports healthy.

        Services with meaningful health semantics (e.g. a model server that
        can be overloaded) should override this.
        """

        return ServiceHealth(name=self.name, status=HealthStatus.HEALTHY)


class ServiceRegistry:
    """Registers services and orchestrates dependency-ordered start/stop."""

    def __init__(self) -> None:
        self._services: dict[str, IService] = {}
        self._started: list[str] = []

    def register(self, service: IService) -> None:
        """Add *service* to the registry.

        Raises:
            ServiceAlreadyRegisteredError: if a service with the same name
                is already registered.
        """

        if service.name in self._services:
            raise ServiceAlreadyRegisteredError(service.name)
        self._services[service.name] = service
        logger.debug("Registered service '%s'.", service.name)

    def unregister(self, name: str) -> None:
        """Remove a service from the registry by name.

        Raises:
            ServiceNotFoundError: if no service with *name* is registered.
        """

        if name not in self._services:
            raise ServiceNotFoundError(name)
        del self._services[name]

    def get(self, name: str) -> IService:
        """Look up a registered service by name.

        Raises:
            ServiceNotFoundError: if no service with *name* is registered.
        """

        try:
            return self._services[name]
        except KeyError as exc:
            raise ServiceNotFoundError(name) from exc

    def all(self) -> tuple[IService, ...]:
        """Return every registered service, in registration order."""

        return tuple(self._services.values())

    def resolve_start_order(self) -> list[str]:
        """Topologically sort registered services by declared dependencies.

        Raises:
            ServiceNotFoundError: if a service declares a dependency that is
                not registered.
            CircularDependencyError: if the dependency graph has a cycle.
        """

        visited: dict[str, int] = {}  # 0 = in progress, 1 = done
        order: list[str] = []
        stack: list[str] = []

        def visit(name: str) -> None:
            state = visited.get(name)
            if state == 1:
                return
            if state == 0:
                cycle = stack[stack.index(name) :] + [name]
                raise CircularDependencyError(cycle)

            if name not in self._services:
                raise ServiceNotFoundError(name)

            visited[name] = 0
            stack.append(name)
            for dependency in self._services[name].dependencies:
                visit(dependency)
            stack.pop()
            visited[name] = 1
            order.append(name)

        for service_name in self._services:
            visit(service_name)

        return order

    async def start_all(self) -> None:
        """Start every registered service in dependency order.

        If any service fails to start, all previously started services in
        this call are stopped (in reverse order) before the error propagates,
        so the registry never ends up in a half-started state.
        """

        order = self.resolve_start_order()
        for name in order:
            service = self._services[name]
            logger.info("Starting service '%s'.", name)
            try:
                await service.start()
            except Exception as exc:  # noqa: BLE001
                logger.error("Service '%s' failed to start: %s", name, exc)
                await self._rollback_started()
                raise ServiceStartError(name, exc) from exc
            self._started.append(name)

    async def stop_all(self) -> None:
        """Stop all currently started services in reverse start order.

        Stopping is best-effort: a failure in one service's ``stop()`` is
        logged and does not prevent the remaining services from being
        stopped, because shutdown must always make forward progress.
        """

        errors: list[ServiceStopError] = []
        for name in reversed(self._started):
            service = self._services[name]
            logger.info("Stopping service '%s'.", name)
            try:
                await service.stop()
            except Exception as exc:  # noqa: BLE001
                logger.error("Service '%s' failed to stop: %s", name, exc)
                errors.append(ServiceStopError(name, exc))
        self._started.clear()
        if errors:
            logger.warning("%d service(s) failed to stop cleanly.", len(errors))

    async def _rollback_started(self) -> None:
        for name in reversed(self._started):
            service = self._services[name]
            try:
                await service.stop()
            except Exception:  # noqa: BLE001
                logger.exception("Error rolling back service '%s'.", name)
        self._started.clear()

    async def check_health(self) -> list[ServiceHealth]:
        """Run health checks for every registered service.

        Failures in an individual service's health check are captured as an
        ``UNHEALTHY`` result rather than raised, so one bad service cannot
        prevent reporting on the rest.
        """

        results: list[ServiceHealth] = []
        for service in self._services.values():
            try:
                results.append(await service.health_check())
            except Exception as exc:  # noqa: BLE001
                logger.exception("Health check failed for '%s'.", service.name)
                results.append(
                    ServiceHealth(
                        name=service.name,
                        status=HealthStatus.UNHEALTHY,
                        message=str(exc),
                    )
                )
        return results
