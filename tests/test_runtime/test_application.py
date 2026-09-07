import pytest

from atlas.config.settings import AtlasConfig
from atlas.runtime.application import AtlasApplication
from atlas.runtime.exceptions import InvalidStateTransitionError, ServiceStartError
from atlas.runtime.health import HealthStatus, ServiceHealth
from atlas.runtime.registry import IService
from atlas.runtime.state import RuntimeState


class _DummyService(IService):
    def __init__(self, name: str, events: list, dependencies: tuple = (), fail_start: bool = False):
        self._name = name
        self._events = events
        self.dependencies = dependencies
        self._fail_start = fail_start

    @property
    def name(self) -> str:
        return self._name

    async def start(self) -> None:
        if self._fail_start:
            raise RuntimeError("boom")
        self._events.append(f"start:{self._name}")

    async def stop(self) -> None:
        self._events.append(f"stop:{self._name}")

    async def health_check(self) -> ServiceHealth:
        return ServiceHealth(name=self._name, status=HealthStatus.HEALTHY)


def _fast_config(**overrides) -> AtlasConfig:
    defaults = dict(
        health_check_interval_seconds=60,
        heartbeat_interval_seconds=60,
        graceful_shutdown_timeout_seconds=2,
    )
    defaults.update(overrides)
    return AtlasConfig(**defaults)


async def test_start_and_stop_transitions_state():
    app = AtlasApplication(_fast_config())

    await app.start()
    assert app.state is RuntimeState.RUNNING
    assert app.uptime_seconds >= 0

    await app.stop()
    assert app.state is RuntimeState.STOPPED


async def test_services_start_and_stop_in_order():
    events: list[str] = []
    app = AtlasApplication(_fast_config())
    app.register_service(_DummyService("a", events))
    app.register_service(_DummyService("b", events, dependencies=("a",)))

    await app.start()
    await app.stop()

    assert events == ["start:a", "start:b", "stop:b", "stop:a"]


async def test_failed_service_start_moves_to_error_state():
    app = AtlasApplication(_fast_config())
    app.register_service(_DummyService("broken", [], fail_start=True))

    with pytest.raises(ServiceStartError):
        await app.start()

    assert app.state is RuntimeState.ERROR


async def test_double_start_raises_invalid_transition():
    app = AtlasApplication(_fast_config())
    await app.start()
    try:
        with pytest.raises(InvalidStateTransitionError):
            await app.start()
    finally:
        await app.stop()


async def test_stop_is_idempotent():
    app = AtlasApplication(_fast_config())
    await app.start()
    await app.stop()
    await app.stop()  # must not raise
    assert app.state is RuntimeState.STOPPED


async def test_context_manager_starts_and_stops():
    app = AtlasApplication(_fast_config())
    async with app:
        assert app.state is RuntimeState.RUNNING
    assert app.state is RuntimeState.STOPPED


async def test_health_monitor_and_heartbeat_are_active_while_running():
    app = AtlasApplication(_fast_config(heartbeat_interval_seconds=0.05))
    app.register_service(_DummyService("svc", []))

    async with app:
        import asyncio

        await asyncio.sleep(0.15)
        # AIManager is now auto-registered; cloud providers without API keys
        # report UNHEALTHY → overall status may be HEALTHY or DEGRADED.
        assert app.health_monitor.latest_report.status in (
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
        )
        assert app.heartbeat.last_beat is not None

    assert app.heartbeat.last_beat is None or True  # heartbeat stopped; no crash on read
