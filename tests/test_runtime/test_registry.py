import pytest

from atlas.runtime.exceptions import (
    CircularDependencyError,
    ServiceAlreadyRegisteredError,
    ServiceNotFoundError,
    ServiceStartError,
)
from atlas.runtime.health import HealthStatus
from atlas.runtime.registry import IService, ServiceRegistry


class _RecordingService(IService):
    def __init__(
        self,
        name: str,
        dependencies: tuple[str, ...] = (),
        events: list | None = None,
        fail_start: bool = False,
        fail_stop: bool = False,
        fail_health: bool = False,
    ):
        self._name = name
        self.dependencies = dependencies
        self._events = events if events is not None else []
        self._fail_start = fail_start
        self._fail_stop = fail_stop
        self._fail_health = fail_health

    @property
    def name(self) -> str:
        return self._name

    async def start(self) -> None:
        if self._fail_start:
            raise RuntimeError(f"{self._name} failed to start")
        self._events.append(f"start:{self._name}")

    async def stop(self) -> None:
        if self._fail_stop:
            raise RuntimeError(f"{self._name} failed to stop")
        self._events.append(f"stop:{self._name}")

    async def health_check(self):
        if self._fail_health:
            raise RuntimeError(f"{self._name} health check exploded")
        return await super().health_check()


def test_register_duplicate_name_raises():
    registry = ServiceRegistry()
    registry.register(_RecordingService("a"))
    with pytest.raises(ServiceAlreadyRegisteredError):
        registry.register(_RecordingService("a"))


def test_get_missing_service_raises():
    registry = ServiceRegistry()
    with pytest.raises(ServiceNotFoundError):
        registry.get("nope")


def test_unregister_missing_service_raises():
    registry = ServiceRegistry()
    with pytest.raises(ServiceNotFoundError):
        registry.unregister("nope")


def test_start_order_respects_dependencies():
    registry = ServiceRegistry()
    registry.register(_RecordingService("db"))
    registry.register(_RecordingService("api", dependencies=("db",)))
    registry.register(_RecordingService("worker", dependencies=("api", "db")))

    order = registry.resolve_start_order()

    assert order.index("db") < order.index("api") < order.index("worker")


def test_cycle_detection():
    registry = ServiceRegistry()
    registry.register(_RecordingService("a", dependencies=("b",)))
    registry.register(_RecordingService("b", dependencies=("a",)))

    with pytest.raises(CircularDependencyError):
        registry.resolve_start_order()


def test_missing_dependency_raises_service_not_found():
    registry = ServiceRegistry()
    registry.register(_RecordingService("a", dependencies=("ghost",)))

    with pytest.raises(ServiceNotFoundError):
        registry.resolve_start_order()


async def test_start_all_runs_in_dependency_order():
    events: list[str] = []
    registry = ServiceRegistry()
    registry.register(_RecordingService("db", events=events))
    registry.register(_RecordingService("api", dependencies=("db",), events=events))

    await registry.start_all()

    assert events == ["start:db", "start:api"]


async def test_failed_start_rolls_back_previously_started():
    events: list[str] = []
    registry = ServiceRegistry()
    registry.register(_RecordingService("db", events=events))
    registry.register(
        _RecordingService("api", dependencies=("db",), events=events, fail_start=True)
    )

    with pytest.raises(ServiceStartError):
        await registry.start_all()

    assert events == ["start:db", "stop:db"]


async def test_stop_all_is_best_effort():
    events: list[str] = []
    registry = ServiceRegistry()
    registry.register(_RecordingService("db", events=events))
    registry.register(
        _RecordingService("api", dependencies=("db",), events=events, fail_stop=True)
    )

    await registry.start_all()
    await registry.stop_all()

    assert "start:db" in events and "start:api" in events
    assert "stop:db" in events  # db still stopped despite api failing to stop


async def test_check_health_reports_default_healthy():
    registry = ServiceRegistry()
    registry.register(_RecordingService("db"))

    results = await registry.check_health()

    assert results[0].status is HealthStatus.HEALTHY


async def test_check_health_catches_exceptions_as_unhealthy():
    registry = ServiceRegistry()
    registry.register(_RecordingService("flaky", fail_health=True))

    results = await registry.check_health()

    assert results[0].status is HealthStatus.UNHEALTHY
    assert "exploded" in (results[0].message or "")
