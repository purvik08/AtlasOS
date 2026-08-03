# Atlas OS

**Atlas OS** is a modular, offline-first AI edge operating system for the
Raspberry Pi 5. It runs multiple local LLMs, exposes a local API and web
dashboard, supports voice interaction, and is built to be extended through a
plugin system -- all without requiring a connection to the cloud.

This is not a demo. It is designed and built the way a production embedded
system should be: clean architecture, dependency injection, explicit
interfaces, and every module independently testable.

> **Status:** Early build. Only the **Runtime Core** module is implemented
> so far. See [Roadmap](#roadmap) below for what's next.

---

## Why Atlas OS

Most "AI on a Pi" projects are a single Python script wired directly to
`llama.cpp`. Atlas OS is instead built as a real operating-system layer:
a supervised application lifecycle, a service registry with dependency
ordering, health monitoring, and a plugin architecture, so that model
serving, voice, networking, and the dashboard can all be developed,
tested, and swapped out independently.

## Current module: Runtime Core

The Runtime Core (`src/atlas/runtime/`) is the foundation every other
module builds on. It provides:

| Component | Responsibility |
|---|---|
| `AtlasApplication` | Composition root; orchestrates startup and graceful shutdown. |
| `LifecycleManager` | Validated state machine (`UNINITIALIZED` → ... → `RUNNING` → ... → `STOPPED`) plus ordered startup/shutdown hooks. |
| `DependencyContainer` | Explicit dependency injection: instance and factory bindings, singleton/transient scope. |
| `ServiceRegistry` | Registers `IService` implementations and starts/stops them in dependency order, with rollback on failure. |
| `HealthMonitor` | Periodically polls every registered service's health and caches an aggregated report. |
| `HeartbeatService` | Emits a periodic liveness tick, independent of service health. |
| `BackgroundTaskManager` | Supervises long-running `asyncio` tasks with restart policies and exponential backoff. |
| `ShutdownSignalHandler` | Cross-platform SIGINT/SIGTERM handling for graceful shutdown. |

See [`docs/architecture/runtime-core.md`](docs/architecture/runtime-core.md)
for the full design rationale, state diagram, and startup/shutdown sequence.

## Project layout

```
AtlasOS/
├── src/atlas/
│   ├── runtime/    # Implemented -- application lifecycle, DI, services, health
│   ├── config/     # Implemented -- settings schema + YAML/env loader
│   ├── logging/    # Implemented -- structured logging setup
│   ├── api/        # Reserved for the Local API module
│   ├── ai/         # Reserved for the Local LLM module
│   ├── voice/      # Reserved for the Voice module
│   ├── memory/     # Reserved for the Memory module
│   ├── mqtt/       # Reserved for the IoT/MQTT module
│   ├── network/    # Reserved for the Network module
│   ├── ui/         # Reserved for the Web Dashboard module
│   ├── plugins/    # Reserved for the Plugin System module
│   ├── auth/       # Reserved for the Auth module
│   ├── models/     # Reserved for domain/data models shared across modules
│   ├── services/   # Reserved for cross-cutting application services
│   └── utils/      # Reserved for shared utilities
├── configs/        # atlas.yaml default configuration
├── docs/           # Architecture and developer documentation
├── tests/          # Unit and integration tests, mirroring src/atlas
├── models/         # Local GGUF model files (empty until the Local LLM module)
├── plugins/        # Installed plugins (empty until the Plugin module)
├── logs/           # Runtime log output
├── systemd/        # Reserved for the Deployment module's unit files
├── docker/         # Reserved for the Deployment module's Dockerfiles
└── scripts/        # Developer scripts (e.g. demo_runtime.py)
```

## Getting started

Requires Python 3.12+. (The project targets 3.13+ for the full OS; the
Runtime Core module itself only needs 3.12+ and was developed against 3.12.)

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run the test suite
pytest

# See the runtime lifecycle in action
python scripts/demo_runtime.py
```

Configuration is loaded from `configs/atlas.yaml` by default and can be
overridden with `ATLAS_`-prefixed environment variables, e.g.:

```bash
ATLAS_LOG_LEVEL=DEBUG ATLAS_HEARTBEAT_INTERVAL_SECONDS=2 python scripts/demo_runtime.py
```

## Roadmap

Modules are built one at a time, each production-ready with its own tests
and docs before the next one starts:

1. ✅ **Runtime Core** -- application lifecycle, DI, service registry, health, heartbeat
2. ⬜ Local LLM (model manager, llama.cpp engine, per-model API ports)
3. ⬜ Local API (FastAPI REST + WebSocket, auth, versioning)
4. ⬜ CLI (`atlas start`, `atlas model`, `atlas status`, ...)
5. ⬜ Voice (wake word, STT, TTS, conversation mode)
6. ⬜ Network (WiFi client/AP, captive portal, mDNS)
7. ⬜ Web Dashboard
8. ⬜ Plugin System
9. ⬜ MQTT / IoT Hub
10. ⬜ Memory (conversation + semantic search)
11. ⬜ Deployment (Docker, systemd, Raspberry Pi image)

## License

MIT
