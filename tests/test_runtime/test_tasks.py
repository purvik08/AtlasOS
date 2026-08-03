import asyncio

from atlas.runtime.tasks import BackgroundTaskManager, RestartPolicy


async def test_task_runs_to_completion():
    manager = BackgroundTaskManager()
    ran = asyncio.Event()

    async def work():
        ran.set()

    manager.spawn("t1", work, restart_policy=RestartPolicy.NEVER)
    await asyncio.wait_for(ran.wait(), timeout=1.0)
    await manager.shutdown()


async def test_task_restarts_on_failure():
    manager = BackgroundTaskManager(base_backoff_seconds=0.01, max_backoff_seconds=0.02)
    attempts = []

    async def flaky():
        attempts.append(1)
        if len(attempts) < 3:
            raise RuntimeError("transient failure")

    manager.spawn("flaky", flaky, restart_policy=RestartPolicy.ON_FAILURE, max_restarts=5)

    for _ in range(100):
        if len(attempts) >= 3:
            break
        await asyncio.sleep(0.02)

    await manager.shutdown()
    assert len(attempts) >= 3


async def test_max_restarts_is_enforced():
    manager = BackgroundTaskManager(base_backoff_seconds=0.01, max_backoff_seconds=0.01)
    attempts = []

    async def always_fails():
        attempts.append(1)
        raise RuntimeError("boom")

    manager.spawn("dying", always_fails, restart_policy=RestartPolicy.ON_FAILURE, max_restarts=2)

    await asyncio.sleep(0.5)
    await manager.shutdown()

    # initial attempt + 2 restarts = 3 total, then it must stop retrying.
    assert len(attempts) == 3


async def test_never_restart_policy_runs_once_even_on_failure():
    manager = BackgroundTaskManager(base_backoff_seconds=0.01)
    attempts = []

    async def fails_once():
        attempts.append(1)
        raise RuntimeError("boom")

    manager.spawn("once", fails_once, restart_policy=RestartPolicy.NEVER)

    await asyncio.sleep(0.1)
    await manager.shutdown()

    assert len(attempts) == 1


async def test_shutdown_cancels_never_ending_task():
    manager = BackgroundTaskManager()

    async def forever():
        await asyncio.sleep(1000)

    manager.spawn("forever", forever, restart_policy=RestartPolicy.NEVER)
    assert manager.is_running("forever")

    await manager.shutdown(timeout_seconds=1.0)
    assert not manager.is_running("forever")


async def test_duplicate_name_raises():
    import pytest

    manager = BackgroundTaskManager()

    async def noop():
        await asyncio.sleep(0.05)

    manager.spawn("dup", noop, restart_policy=RestartPolicy.NEVER)
    with pytest.raises(ValueError):
        manager.spawn("dup", noop, restart_policy=RestartPolicy.NEVER)

    await manager.shutdown()


async def test_cancel_single_task():
    manager = BackgroundTaskManager()

    async def forever():
        await asyncio.sleep(1000)

    manager.spawn("only", forever, restart_policy=RestartPolicy.NEVER)
    await manager.cancel("only", timeout_seconds=1.0)

    assert not manager.is_running("only")
