# Runtime Core -- Architecture

The Runtime Core is the composition root of Atlas OS. Every other module
(AI, voice, network, UI, plugins, MQTT, ...) is expected to implement
`IService` and register itself with the `AtlasApplication` rather than
managing its own startup, threads, or shutdown logic. This document explains
the design and the reasoning behind it.

## Design goals

- **Predictable startup and shutdown.** No module should have to guess
  whether a dependency is ready. Services declare their dependencies and the
  registry starts them in the correct order -- and rolls back cleanly if one
  fails.
- **No global mutable state.** Everything lives on an `AtlasApplication`
  instance. This makes the runtime testable (spin up an app, assert on it,
  throw it away) and makes multiple isolated runtimes possible in the same
  process, which matters for testing the API and CLI modules later.
- **Shutdown always makes progress.** A failing service, a failing shutdown
  hook, or a stuck background task must never prevent the rest of the system
  from tearing down. Every teardown step in `AtlasApplication.stop()` is
  best-effort and logs rather than aborts.
- **Small, explicit primitives over a framework.** The dependency container
  and service registry are deliberately simple and do not do reflection-based
  auto-wiring. Every binding and every dependency edge is explicit in code.

## Components

### `RuntimeState` (`state.py`)

A `str, Enum` state machine:

```
UNINITIALIZED → INITIALIZING → STARTING → RUNNING ⇄ DEGRADED
                                   ↓           ↓
                                 ERROR ────→ STOPPING → STOPPED → (INITIALIZING)
```

The legal-transition table lives in `_ALLOWED_TRANSITIONS` and is enforced
by `LifecycleManager.transition_to`, which raises
`InvalidStateTransitionError` on an illegal move. `STOPPED → INITIALIZING`
is legal so an `AtlasApplication` can be restarted after a clean stop;
`ERROR → INITIALIZING` is legal for the same reason after a failed start.

### `LifecycleManager` (`lifecycle.py`)

Owns the current `RuntimeStateSnapshot` behind an `asyncio.Lock`, notifies
registered listeners synchronously on every transition, and runs
priority-ordered startup/shutdown hooks that are independent of any specific
service (e.g. "create the data directory" doesn't need to be a full
`IService`).

Startup hooks run once, before service startup begins. Shutdown hooks run
once, after all services have been stopped -- and shutdown hooks are
best-effort: one failing hook does not stop the others from running.

### `DependencyContainer` (`container.py`)

A minimal, explicit DI container keyed by arbitrary hashable values
(typically a class or `Protocol`). Two provider kinds:

- `register_instance(key, value)` -- always returns the same object.
- `register_factory(key, factory, scope=...)` -- calls a sync or async
  zero-argument callable, either once (`Scope.SINGLETON`) or on every
  resolution (`Scope.TRANSIENT`).

Circular resolution (a factory that, directly or indirectly, resolves its
own key while it's already being resolved) is detected and raised as
`DependencyResolutionError` rather than recursing until a `RecursionError`.

This container is intentionally separate from the `ServiceRegistry`: it is
for arbitrary values and helper objects, while the registry is specifically
for things with a start/stop lifecycle.

### `IService` and `ServiceRegistry` (`registry.py`)

`IService` is the contract every long-lived Atlas service implements:

```python
class IService(ABC):
    dependencies: tuple[str, ...] = ()

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    async def health_check(self) -> ServiceHealth: ...  # default: healthy
```

`ServiceRegistry.resolve_start_order()` topologically sorts registered
services by their `dependencies` tuples using iterative DFS with cycle
detection, raising `CircularDependencyError` with the offending cycle if the
graph isn't a DAG.

`start_all()` starts services in that order. If any service's `start()`
raises, every service started so far in that call is stopped again (in
reverse order) before `ServiceStartError` propagates -- the registry never
leaves the system in a half-started state.

`stop_all()` stops started services in reverse order and is best-effort:
a failing `stop()` is logged and collected, but does not prevent the rest
of the services from being stopped.

### `HealthMonitor` (`health.py`)

Polls `ServiceRegistry.check_health()` on a fixed interval and caches the
aggregated `HealthReport` (worst-of every `ServiceHealth`). Reading
`latest_report` is synchronous and non-blocking by design, so it is cheap to
call from a hot path like an HTTP `/health` endpoint without waiting on live
service checks. The first check runs immediately on `start()` rather than
waiting a full interval, so a report is available right away.

### `HeartbeatService` (`heartbeat.py`)

A separate, simpler background tick used to prove the event loop itself is
responsive -- distinct from service health, which asks "is this service
working correctly?" A stalled event loop with healthy-looking services would
still stop producing heartbeats, which is a useful independent signal for
external monitoring (e.g. a systemd watchdog in the Deployment module).

### `BackgroundTaskManager` (`tasks.py`)

Supervises arbitrary `asyncio` tasks that services or the application itself
need to run for the runtime's lifetime (queue consumers, watchdogs, etc.).
Supports three restart policies (`NEVER`, `ON_FAILURE`, `ALWAYS`) with
exponential backoff up to a configurable ceiling, and a restart count cap to
avoid infinite crash loops. `shutdown()` cancels every supervised task with a
timeout and disables further restarts.

### `ShutdownSignalHandler` (`signals.py`)

Installs SIGINT/SIGTERM handling. On POSIX this uses
`loop.add_signal_handler`; on Windows, where that API doesn't exist, it
falls back to `signal.signal`. Both paths schedule the shutdown coroutine via
`loop.call_soon_threadsafe`, so the handling code path is identical
regardless of platform.

### `AtlasApplication` (`application.py`)

The composition root. Owns one instance each of the container, registry,
lifecycle manager, health monitor, heartbeat, and task manager, and
sequences them:

**Startup (`start()`)**
1. `INITIALIZING` → run startup hooks
2. `STARTING` → `registry.start_all()` → `health_monitor.start()` →
   `heartbeat.start()`
3. `RUNNING`

**Shutdown (`stop()`)**
1. `STOPPING`
2. `heartbeat.stop()` → `health_monitor.stop()` →
   `tasks.shutdown(timeout=graceful_shutdown_timeout_seconds)` →
   `registry.stop_all()` → run shutdown hooks
3. `STOPPED`

If any step of startup fails, the application transitions to `ERROR` and
re-raises so the caller (CLI, systemd, tests) knows startup did not
succeed. Every step of shutdown runs regardless of earlier failures.

`run_forever()` installs the signal handler, starts the application, and
blocks on an `asyncio.Event` until `stop()` completes -- this is what
`atlas start` will call once the CLI module exists.

## Configuration

`AtlasConfig` (`atlas/config/settings.py`) is a Pydantic `BaseSettings`
model. `load_config()` (`atlas/config/loader.py`) builds a dynamic subclass
wired to a custom `YamlConfigSettingsSource`, giving this precedence order
(highest to lowest):

1. Keyword overrides passed to `load_config(**overrides)`
2. `ATLAS_`-prefixed environment variables
3. `configs/atlas.yaml`
4. Field defaults on `AtlasConfig`

A missing YAML file is not an error -- Atlas falls back to defaults and
environment variables, since the OS should boot with sane defaults even on
a fresh SD card image before any configuration has been written.

## What's deliberately out of scope here

- **Model serving, voice, networking, dashboard, plugins.** These are
  future `IService` implementations registered with the same
  `AtlasApplication`; none of that logic belongs in the Runtime Core.
- **The CLI.** `atlas start` / `atlas status` / etc. will be a thin wrapper
  around `AtlasApplication.run_forever()` and the health/heartbeat reads,
  built in the CLI module.
- **Persistence.** The registry and container are in-memory; nothing here
  touches disk except the optional YAML config file.
