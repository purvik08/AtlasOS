import asyncio

import pytest

from atlas.runtime.heartbeat import HeartbeatService


async def test_heartbeat_emits_ticks():
    service = HeartbeatService(interval_seconds=0.05)
    beats = []
    service.add_listener(beats.append)

    await service.start()
    try:
        await asyncio.sleep(0.35)
    finally:
        await service.stop()

    assert len(beats) >= 3
    assert service.last_beat is not None
    assert service.seconds_since_last_beat() is not None


async def test_no_beat_before_start():
    service = HeartbeatService(interval_seconds=1.0)
    assert service.last_beat is None
    assert service.seconds_since_last_beat() is None


async def test_stop_before_start_is_safe():
    service = HeartbeatService(interval_seconds=1.0)
    await service.stop()  # should not raise


async def test_double_start_is_idempotent():
    service = HeartbeatService(interval_seconds=1.0)
    await service.start()
    try:
        first_task = service._task  # noqa: SLF001 - white-box check for idempotency
        await service.start()
        assert service._task is first_task  # noqa: SLF001
    finally:
        await service.stop()


def test_non_positive_interval_rejected():
    with pytest.raises(ValueError):
        HeartbeatService(interval_seconds=0)
