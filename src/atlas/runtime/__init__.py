"""Atlas OS runtime core: application lifecycle, DI, services, health.

This is the first module of Atlas OS. It provides the foundation every other
module (AI, voice, network, UI, plugins, ...) builds on: a supervised
application lifecycle, a dependency injection container, a service registry
with ordered start/stop, health monitoring, a heartbeat, background task
supervision, and graceful OS-signal-driven shutdown.
"""

from atlas.runtime.application import AtlasApplication
from atlas.runtime.container import DependencyContainer, Scope
from atlas.runtime.exceptions import (
    AtlasRuntimeError,
    CircularDependencyError,
    DependencyResolutionError,
    InvalidStateTransitionError,
    ServiceAlreadyRegisteredError,
    ServiceNotFoundError,
    ServiceStartError,
    ServiceStopError,
)
from atlas.runtime.health import (
    HealthMonitor,
    HealthReport,
    HealthStatus,
    ServiceHealth,
)
from atlas.runtime.heartbeat import Heartbeat, HeartbeatService
from atlas.runtime.lifecycle import LifecycleManager
from atlas.runtime.registry import IService, ServiceRegistry
from atlas.runtime.signals import ShutdownSignalHandler
from atlas.runtime.state import RuntimeState, RuntimeStateSnapshot
from atlas.runtime.tasks import BackgroundTaskManager, RestartPolicy

__all__ = [
    "AtlasApplication",
    "DependencyContainer",
    "Scope",
    "AtlasRuntimeError",
    "CircularDependencyError",
    "DependencyResolutionError",
    "InvalidStateTransitionError",
    "ServiceAlreadyRegisteredError",
    "ServiceNotFoundError",
    "ServiceStartError",
    "ServiceStopError",
    "HealthMonitor",
    "HealthReport",
    "HealthStatus",
    "ServiceHealth",
    "Heartbeat",
    "HeartbeatService",
    "LifecycleManager",
    "IService",
    "ServiceRegistry",
    "ShutdownSignalHandler",
    "RuntimeState",
    "RuntimeStateSnapshot",
    "BackgroundTaskManager",
    "RestartPolicy",
]
