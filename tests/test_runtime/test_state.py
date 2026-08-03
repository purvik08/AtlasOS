from atlas.runtime.state import RuntimeState, is_transition_allowed


def test_uninitialized_can_only_move_to_initializing():
    assert is_transition_allowed(RuntimeState.UNINITIALIZED, RuntimeState.INITIALIZING)
    assert not is_transition_allowed(RuntimeState.UNINITIALIZED, RuntimeState.RUNNING)


def test_running_can_degrade_and_stop():
    assert is_transition_allowed(RuntimeState.RUNNING, RuntimeState.DEGRADED)
    assert is_transition_allowed(RuntimeState.RUNNING, RuntimeState.STOPPING)
    assert not is_transition_allowed(RuntimeState.RUNNING, RuntimeState.INITIALIZING)


def test_stopped_can_restart():
    assert is_transition_allowed(RuntimeState.STOPPED, RuntimeState.INITIALIZING)


def test_error_can_be_recovered_from():
    assert is_transition_allowed(RuntimeState.ERROR, RuntimeState.STOPPING)
    assert is_transition_allowed(RuntimeState.ERROR, RuntimeState.INITIALIZING)
    assert not is_transition_allowed(RuntimeState.ERROR, RuntimeState.RUNNING)
