# Atlas OS

<div align="center">

**A modular, offline-first AI edge operating system for the Raspberry Pi 5.**

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![PySide6](https://img.shields.io/badge/PySide6-Qt%2FQML-41CD52?logo=qt)](https://doc.qt.io/qtforpython/)

</div>

---

Atlas OS runs multiple local LLMs, exposes a local REST API, features both a fullscreen touch kiosk UI and a desktop dashboard, supports voice interaction, semantic memory, RAG, and is built to be extended through a plugin system — all without requiring a connection to the cloud.

This is not a demo. It is designed and built the way a production embedded system should be: clean architecture, dependency injection, explicit interfaces, and every module independently testable.

---

## What's Implemented

| Module | Status | Description |
|--------|--------|-------------|
| **Runtime Core** | ✅ Done | Application lifecycle, DI container, service registry, health monitor, heartbeat, background tasks |
| **Config** | ✅ Done | Pydantic settings schema + YAML / env-var loader with full precedence chain |
| **Logging** | ✅ Done | Structured logging setup (JSON + human-readable modes) |
| **AI Engine** | ✅ Done | Multi-provider LLM router, session management, conversation history, model downloader, model selector |
| **AI Providers** | ✅ Done | 35+ cloud & local providers (see full list below) |
| **AI Tools** | ✅ Done | Agentic tool layer: system, model, network, plugin, voice, RAG, runtime tools |
| **CLI** | ✅ Done | Full `atlas` CLI — runtime, models, AI chat, network, voice, plugins, config, kiosk, desktop |
| **API** | ✅ Done | FastAPI REST + WebSocket: auth, chat, models, memory, network, plugins, providers, RAG, sessions, terminal, voice |
| **Auth** | ✅ Done | JWT authentication, middleware, user model management |
| **Kiosk UI** | ✅ Done | Fullscreen Qt/QML touch interface — 7 screens (Home, Chat, Memory, Models, Network, System, Voice) |
| **Desktop UI** | ✅ Done | Qt/QML Material dashboard — 11 panels (Chat, Config, Logs, Memory, Models, Network, Plugins, Providers, Runtime, System, Voice) |
| **Core App** | ✅ Done | `atlas.core.app` — top-level composition root wiring all services |
| **Memory** | ✅ Done | Conversation history, semantic embeddings, models, RAG store, vector search |
| **RAG** | ✅ Done | Retrieval-augmented generation service with document store |
| **Network** | ✅ Done | WiFi client/AP mode, mDNS, monitor, NetworkManager backend, WPA supplicant |
| **Plugins** | ✅ Done | Plugin core: registry, base classes, permissions system |
| **Secrets** | ✅ Done | Secure API key storage (keyring + encrypted file fallback) |
| **Voice** | ✅ Done | Wake word (openwakeword), STT (faster-whisper), TTS (piper-tts), audio backend |
| **Update** | ✅ Done | OTA update mechanism |
| **Image Builder** | ✅ Done | pi-gen pipeline that produces a flashable `AtlasOS.img.xz` for Raspberry Pi 5 |
| **Systemd** | ✅ Done | `atlas-kiosk.service` + `atlas-firstboot.service` for auto-start on boot |
| **Docker** | ✅ Done | `Dockerfile` + `docker-compose.yml` for containerized development |
| **MQTT** | 🔧 Placeholder | IoT hub (interface stubbed, implementation pending) |

---

## Why Atlas OS

Most "AI on a Pi" projects are a single Python script wired directly to `llama.cpp`.
Atlas OS is instead built as a real operating-system layer:
a supervised application lifecycle, a service registry with dependency ordering, health monitoring,
and a plugin architecture — so that model serving, voice, networking, and the UI
can all be developed, tested, and swapped out independently.

---

## AI Providers

The AI engine supports **35+ cloud and local providers**, with an auto-routing strategy
that prefers local models and falls back to cloud when needed.

### Local
| Provider | Description |
|----------|-------------|
| `llama_cpp` | GGUF models via llama-cpp-python; compiled with OpenBLAS on Pi 5 |

### Cloud
| Provider | Provider | Provider | Provider |
|----------|----------|----------|----------|
| `openai` | `anthropic` | `gemini` / `google_ai` | `azure_openai` |
| `groq` | `mistral` | `cohere` / `cohere_compat` | `deepseek` |
| `together` | `fireworks` | `openrouter` | `perplexity` |
| `anyscale` | `bedrock` | `vertex_ai` | `nvidia` |
| `cerebras` | `ai21` / `ai21_compat` | `deepinfra` | `lepton` |
| `friendliai` | `novita` | `replicate` | `sambanova` |
| `kimi` | `qwen` | `xai` | |

Configure providers via `configs/atlas.yaml` or `ATLAS_AI__*` environment variables.

---

## UI

### Kiosk UI (Touch — Raspberry Pi 5)

Fullscreen Qt/QML interface optimised for touch on the Pi's display:

| Screen | Description |
|--------|-------------|
| **Home** | System status overview and animated robot face |
| **Chat** | Real-time AI chat with the active LLM |
| **Models** | Browse, download, and switch GGUF models |
| **Memory** | Conversation history and semantic memory viewer |
| **Network** | WiFi status and configuration |
| **System** | CPU, RAM, temperature, logs |
| **Voice** | Wake word and TTS controls |

```bash
# Development (windowed)
python -m atlas.ui.kiosk.main

# Fullscreen (as it runs on-device)
ATLAS_KIOSK_FULLSCREEN=1 ATLAS_MODELS_DIR=./models python -m atlas.ui.kiosk.main
```

### Desktop UI (Qt/QML Material Dashboard)

Full dashboard for desktop/development use with 11 panels:

```bash
atlas desktop start
```

Panels: Chat, Config, Logs, Memory, Models, Network, Plugins, Providers, Runtime, System, Voice.

---

## CLI Reference

```
atlas start                Start the Atlas OS runtime
atlas version              Show version
atlas runtime status       Show runtime and service health
atlas runtime stop         Graceful shutdown

atlas models list          List available GGUF models
atlas models download      Download a model from HuggingFace
atlas models select        Set the active model

atlas chat                 Interactive AI chat session
atlas provider list        List AI providers and their status

atlas session list         List active chat sessions

atlas memory list          Browse stored memories
atlas memory search        Semantic memory search

atlas config show          Print current configuration
atlas doctor               System health diagnostics

atlas network status       WiFi and connectivity info
atlas network scan         Scan for WiFi networks
atlas network connect      Connect to a WiFi network

atlas voice status         Voice subsystem status
atlas voice wake           Test wake word detection

atlas plugins list         List installed plugins
atlas plugins install      Install a plugin

atlas desktop start        Launch the desktop Qt dashboard
atlas kiosk start          Launch the kiosk UI

atlas logs                 Tail runtime logs
atlas update               Pull latest Atlas OS from GitHub
```

---

## Project Layout

```
AtlasOS/
├── src/atlas/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                  # CLI entry point
│   ├── core/                   # Top-level composition root
│   │   ├── __init__.py
│   │   └── app.py              # AtlasCoreApp — wires all services
│   ├── runtime/                # Lifecycle, DI, registry, health, heartbeat, tasks
│   ├── config/                 # Pydantic settings + YAML/env loader
│   ├── logging/                # Structured logging setup
│   ├── cli/                    # Click subcommands (ai, config, desktop, kiosk, memory,
│   │                           #   models, network, plugins, process_manager, rag,
│   │                           #   runtime, system, voice)
│   ├── ai/                     # AI engine
│   │   ├── engine.py           # Inference engine
│   │   ├── router.py           # Provider auto-router (local → cloud fallback)
│   │   ├── manager.py          # Model lifecycle manager
│   │   ├── session.py          # Chat session management
│   │   ├── history.py          # Conversation history
│   │   ├── model.py            # Model schema
│   │   ├── model_selector.py   # Active model selection logic
│   │   ├── downloader.py       # HuggingFace model downloader
│   │   ├── cache.py            # Inference cache
│   │   ├── prompt.py           # Prompt builder
│   │   ├── resource.py         # Resource manager
│   │   ├── os_ai.py            # OS-level AI integration
│   │   ├── providers/          # 35+ provider implementations
│   │   └── tools/              # Agentic tools (system, model, network, plugin,
│   │                           #   voice, rag, runtime)
│   ├── api/                    # FastAPI REST + WebSocket
│   │   ├── server.py
│   │   ├── auth.py
│   │   ├── sdk.py
│   │   ├── routes/             # auth, chat, memory, models, network, plugins,
│   │   │                       #   providers, rag, sessions, system, terminal, voice
│   │   └── web/                # Embedded web UI assets
│   ├── auth/                   # JWT auth, middleware, models
│   ├── memory/                 # Conversation, embeddings, models, RAG, search
│   ├── rag/                    # RAG document store + service
│   ├── network/                # WiFi, AP, mDNS, monitor, NM backend, WPA
│   ├── voice/                  # Wake word, STT, TTS, audio backend
│   ├── plugins/                # Plugin core: registry, permissions
│   ├── secrets/                # Keyring + encrypted file storage
│   ├── update/                 # OTA update
│   ├── mqtt/                   # IoT MQTT (stub)
│   ├── models/                 # Shared Pydantic models
│   ├── services/               # Shared service interfaces
│   ├── utils/                  # Shared utilities
│   └── ui/
│       ├── kiosk/              # Fullscreen touch kiosk (Qt/QML)
│       │   ├── main.py
│       │   ├── controllers/    # app_state, theme
│       │   ├── models/         # chat_model, llm_model, memory_model, network_model
│       │   └── qml/            # Main.qml, screens/, components/
│       ├── dashboard/          # Desktop Qt/QML Material dashboard
│       │   ├── main.py
│       │   ├── cli/
│       │   ├── controllers/    # app_state, theme
│       │   ├── models/         # chat, llm, memory, network, terminal models
│       │   ├── services/       # api_service.py
│       │   └── resources/qml/  # Main.qml, panels/, screens/, components/
│       └── desktop/            # Legacy desktop UI (Qt/QML)
│           ├── main.py
│           ├── cli/
│           ├── models/
│           └── resources/qml/  # Main.qml, panels/ (11 panels)
├── configs/
│   └── atlas.yaml              # Runtime configuration
├── data/                       # Runtime data (model registry, memory DB, users)
├── docs/
│   └── architecture/           # runtime-core.md, raspberrypi5-arm64.md
├── image/                      # pi-gen image builder → AtlasOS.img.xz
│   └── stage-atlas/            # 4 build stages: base, install, kiosk, splash
├── models/                     # GGUF model files (populated after flash/download)
├── plugins/                    # Installed plugins
├── logs/                       # Runtime log output
├── scripts/
│   ├── demo_runtime.py         # Runtime lifecycle demo
│   ├── capture_kiosk_screens.py
│   ├── generate_openapi.py     # OpenAPI spec generator
│   ├── first-boot.sh           # First-boot provisioning script
│   └── start-kiosk.sh
├── systemd/                    # atlas-kiosk.service, atlas-firstboot.service
├── docker/                     # Docker support files
├── tests/                      # Full test suite mirroring src/atlas
│   ├── test_ai/
│   ├── test_api/
│   ├── test_auth/
│   ├── test_cli/
│   ├── test_memory/
│   ├── test_network/
│   ├── test_plugins/
│   ├── test_rag/
│   ├── test_runtime/
│   ├── test_ui/
│   └── test_voice/
├── Dockerfile
├── Dockerfile.dev
├── docker-compose.yml
├── docker-compose.dev.yml
├── Makefile
├── pyproject.toml
├── pyrightconfig.json
├── requirements-optional.txt
└── README.md
```

---

## Getting Started

**Requires Python 3.12+.**

```bash
# Clone the repo
git clone https://github.com/purvik08/AtlasOS.git
cd AtlasOS

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run the test suite
pytest

# See the runtime lifecycle in action
python scripts/demo_runtime.py

# Launch the kiosk UI (development, windowed)
python -m atlas.ui.kiosk.main

# Launch the desktop dashboard
atlas desktop start
```

### Configuration

Configuration is loaded from `configs/atlas.yaml` and can be overridden with `ATLAS_`-prefixed
environment variables (highest precedence):

```bash
# Example overrides
ATLAS_LOG_LEVEL=DEBUG
ATLAS_AI__DEFAULT_PROVIDER=gemini
ATLAS_AI__GEMINI_API_KEY=your-key-here
ATLAS_AI__DEFAULT_MODEL=llama-3.2-3b
ATLAS_HEARTBEAT_INTERVAL_SECONDS=2
```

Precedence order: **env vars** → **atlas.yaml** → **field defaults**

### Optional Extras

```bash
# Local inference (llama.cpp) — Raspberry Pi 5 (CPU + OpenBLAS):
CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS" pip install llama-cpp-python
pip install -e ".[local]"

# Voice (wake word, STT, TTS)
pip install -e ".[voice]"

# MQTT
pip install -e ".[mqtt]"

# Everything
pip install -e ".[all]"
```

---

## Flashing to Raspberry Pi 5

Build a flashable image directly on the Pi:

```bash
# One-time setup
make -f image/Makefile image-setup

# Build (~50 minutes)
make -f image/Makefile image-build
# Output: ~/pi-gen/deploy/AtlasOS-*.img.xz
```

**Flash with Raspberry Pi Imager** (Windows / macOS / Linux) → Choose OS → Use custom → select `.img.xz`.

After boot:
1. Wait ~90 seconds for first-boot provisioning (auto-reboots once)
2. Plymouth splash → kiosk appears fullscreen
3. Copy GGUF models over SSH:
   ```bash
   scp model.gguf atlas@<PI-IP>:/home/atlas/AtlasOS/models/
   # default password: atlas123
   ```

See [`image/README.md`](image/README.md) for the full build and troubleshooting guide.

---

## Docker

```bash
# Production
docker compose up

# Development (hot reload)
docker compose -f docker-compose.dev.yml up
```

See [`DOCKER.md`](DOCKER.md) for details.

---

## Development

```bash
# Type checking
mypy src/

# Linting + auto-fix
ruff check src/
ruff check --fix src/

# Run all tests
pytest

# Run specific test modules
pytest tests/test_ai/
pytest tests/test_runtime/
pytest tests/test_api/
pytest tests/test_memory/

# Generate OpenAPI spec
python scripts/generate_openapi.py
```

---

## Architecture

### Runtime Core

See [`docs/architecture/runtime-core.md`](docs/architecture/runtime-core.md) for the full
design rationale, state diagram, and startup/shutdown sequence.

| Component | Responsibility |
|-----------|----------------|
| `AtlasApplication` | Composition root — orchestrates startup and graceful shutdown |
| `LifecycleManager` | Validated state machine (`UNINITIALIZED → RUNNING → STOPPED`) with ordered hooks |
| `DependencyContainer` | Explicit DI: instance and factory bindings, singleton/transient scope |
| `ServiceRegistry` | Starts/stops `IService` implementations in dependency order, with rollback on failure |
| `HealthMonitor` | Periodically polls every service's health and caches an aggregated report |
| `HeartbeatService` | Emits a periodic liveness tick, independent of service health |
| `BackgroundTaskManager` | Supervises long-running asyncio tasks with restart policies and exponential backoff |
| `ShutdownSignalHandler` | Cross-platform SIGINT/SIGTERM handling for graceful shutdown |

### AI Engine

The AI engine uses a **local-first routing strategy**:

```
Request
  └─► ModelSelector — picks the best available model
        └─► Router ─► Local (llama.cpp) ──► fast, private, offline
                   └─► Cloud fallback ──► 35+ providers via unified API
```

Sessions maintain conversation history with configurable context windows. The tool layer allows the AI to interact with OS subsystems (network, plugins, voice, runtime) as an agentic assistant.

### API

Full REST + WebSocket API served by FastAPI:

| Route prefix | Description |
|-------------|-------------|
| `/v1/auth` | Login, token refresh |
| `/v1/chat` | Chat completions (streaming + WebSocket) |
| `/v1/models` | Model list, download, activation |
| `/v1/memory` | Memory read/write/search |
| `/v1/network` | WiFi scan, connect, status |
| `/v1/plugins` | Plugin install/list/enable |
| `/v1/providers` | Provider list and status |
| `/v1/rag` | Document ingestion and retrieval |
| `/v1/sessions` | Session management |
| `/v1/system` | System metrics and logs |
| `/v1/terminal` | Terminal WebSocket |
| `/v1/voice` | Wake word + TTS control |

---

## Changelog

See [`CHANGELOG.md`](CHANGELOG.md) for the full version history.

**Latest: v1.2.0** — Desktop UI (Qt/QML Material), full provider suite (35+ providers), agentic tools layer, complete memory + RAG + network modules.

---

## License

MIT — © Purvik
