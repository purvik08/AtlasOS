import pytest

from atlas.runtime.exceptions import InvalidStateTransitionError
from atlas.runtime.lifecycle import LifecycleManager
from atlas.runtime.state import RuntimeState


async def test_valid_transition_updates_state():
    manager = LifecycleManager()
    await manager.transition_to(RuntimeState.INITIALIZING)
    assert manager.state is RuntimeState.INITIALIZING


async def test_invalid_transition_raises():
    manager = LifecycleManager()
    with pytest.raises(InvalidStateTransitionError):
        await manager.transition_to(RuntimeState.RUNNING)


async def test_listeners_receive_transitions():
    manager = LifecycleManager()
    seen = []
    manager.add_listener(lambda before, after: seen.append((before.state, after.state)))

    await manager.transition_to(RuntimeState.INITIALIZING)

    assert seen == [(RuntimeState.UNINITIALIZED, RuntimeState.INITIALIZING)]


async def test_removed_listener_is_not_notified():
    manager = LifecycleManager()
    seen = []
    listener = lambda before, after: seen.append((before.state, after.state))  # noqa: E731
    manager.add_listener(listener)
    manager.remove_listener(listener)

    await manager.transition_to(RuntimeState.INITIALIZING)

    assert seen == []


async def test_startup_hooks_run_in_priority_order():
    manager = LifecycleManager()
    order = []

    async def first():
        order.append("first")

    async def second():
        order.append("second")

    manager.register_startup_hook(second, name="second", priority=20)
    manager.register_startup_hook(first, name="first", priority=10)

    await manager.run_startup_hooks()

    assert order == ["first", "second"]


async def test_equal_priority_hooks_run_in_registration_order():
    manager = LifecycleManager()
    order = []

    async def a():
        order.append("a")

    async def b():
        order.append("b")

    manager.register_startup_hook(a, name="a", priority=10)
    manager.register_startup_hook(b, name="b", priority=10)

    await manager.run_startup_hooks()

    assert order == ["a", "b"]


async def test_shutdown_hooks_continue_after_failure():
    manager = LifecycleManager()
    order = []

    async def failing():
        order.append("failing")
        raise RuntimeError("boom")

    async def cleanup():
        order.append("cleanup")

    manager.register_shutdown_hook(failing, name="failing", priority=1)
    manager.register_shutdown_hook(cleanup, name="cleanup", priority=2)

    await manager.run_shutdown_hooks()

    assert order == ["failing", "cleanup"]
