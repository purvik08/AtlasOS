from atlas.runtime.health import HealthMonitor, HealthReport, HealthStatus, ServiceHealth


class _FakeRegistry:
    def __init__(self, results):
        self._results = results

    async def check_health(self):
        return self._results


def test_aggregate_reports_worst_status():
    services = [
        ServiceHealth(name="a", status=HealthStatus.HEALTHY),
        ServiceHealth(name="b", status=HealthStatus.DEGRADED),
    ]

    report = HealthReport.aggregate(services)

    assert report.status is HealthStatus.DEGRADED


def test_aggregate_unhealthy_beats_degraded():
    services = [
        ServiceHealth(name="a", status=HealthStatus.DEGRADED),
        ServiceHealth(name="b", status=HealthStatus.UNHEALTHY),
    ]

    report = HealthReport.aggregate(services)

    assert report.status is HealthStatus.UNHEALTHY


def test_aggregate_empty_is_unknown():
    report = HealthReport.aggregate([])
    assert report.status is HealthStatus.UNKNOWN


async def test_monitor_polls_immediately_on_start():
    registry = _FakeRegistry([ServiceHealth(name="a", status=HealthStatus.HEALTHY)])
    monitor = HealthMonitor(registry, interval_seconds=60)

    await monitor.start()
    try:
        assert monitor.latest_report.status is HealthStatus.HEALTHY
    finally:
        await monitor.stop()


async def test_monitor_notifies_listeners():
    registry = _FakeRegistry([ServiceHealth(name="a", status=HealthStatus.HEALTHY)])
    monitor = HealthMonitor(registry, interval_seconds=60)
    seen = []
    monitor.add_listener(seen.append)

    await monitor.start()
    try:
        assert len(seen) == 1
        assert seen[0].status is HealthStatus.HEALTHY
    finally:
        await monitor.stop()


async def test_stop_before_start_is_safe():
    registry = _FakeRegistry([])
    monitor = HealthMonitor(registry, interval_seconds=60)
    await monitor.stop()  # should not raise


def test_negative_interval_rejected():
    import pytest

    with pytest.raises(ValueError):
        HealthMonitor(_FakeRegistry([]), interval_seconds=0)
