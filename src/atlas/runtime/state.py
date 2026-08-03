"""Runtime state machine primitives for Atlas OS.

This module defines the finite set of states the ``AtlasApplication`` can be
in, the table of legal transitions between them, and a lightweight immutable
snapshot type used to report state to callers (CLI, API, dashboard).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class RuntimeState(str, Enum):
    """Discrete lifecycle states of the Atlas runtime."""

    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


#: Table of legal state transitions. Keys are the current state, values are
#: the set of states that may be transitioned to from that state.
_ALLOWED_TRANSITIONS: dict[RuntimeState, frozenset[RuntimeState]] = {
    RuntimeState.UNINITIALIZED: frozenset({RuntimeState.INITIALIZING}),
    RuntimeState.INITIALIZING: frozenset({RuntimeState.STARTING, RuntimeState.ERROR}),
    RuntimeState.STARTING: frozenset(
        {RuntimeState.RUNNING, RuntimeState.ERROR, RuntimeState.STOPPING}
    ),
    RuntimeState.RUNNING: frozenset(
        {RuntimeState.DEGRADED, RuntimeState.STOPPING, RuntimeState.ERROR}
    ),
    RuntimeState.DEGRADED: frozenset(
        {RuntimeState.RUNNING, RuntimeState.STOPPING, RuntimeState.ERROR}
    ),
    RuntimeState.STOPPING: frozenset({RuntimeState.STOPPED, RuntimeState.ERROR}),
    RuntimeState.STOPPED: frozenset({RuntimeState.INITIALIZING}),
    RuntimeState.ERROR: frozenset({RuntimeState.STOPPING, RuntimeState.INITIALIZING}),
}


def is_transition_allowed(current: RuntimeState, target: RuntimeState) -> bool:
    """Return ``True`` if moving from *current* to *target* is legal."""

    return target in _ALLOWED_TRANSITIONS.get(current, frozenset())


@dataclass(frozen=True, slots=True)
class RuntimeStateSnapshot:
    """An immutable point-in-time view of the runtime's state."""

    state: RuntimeState
    since: float = field(default_factory=time.monotonic)
    reason: str | None = None

    def age_seconds(self) -> float:
        """Seconds elapsed since this state was entered."""

        return time.monotonic() - self.since
