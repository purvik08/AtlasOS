# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2025-08-17

### Added
- **Desktop UI (Qt/QML + Material style)**: 4-panel dashboard (System, Models, Providers, Chat)
- **Kiosk UI (touch-optimized)**: 4 controllers (System, Model, Provider, Session) + dashboard
- Qt Quick Controls 2 Material style integration (`QT_QUICK_CONTROLS_STYLE=Material`)
- CLI `atlas desktop start/status` commands
- API root endpoint (`/`) redirecting to `/v1/health` with API info
- Retry counter fix (1/3 → 2/3 → 3/3) + monitor task singleton
- API key propagation to backend + desktop subprocesses
- CLI args now propagate via env vars (`ATLAS_API_URL`, `ATLAS_API_KEY`)
- `requirements-optional.txt` for Voice/Network extras
- Auto-generated OpenAPI spec at `/docs` (Swagger UI) and `/redoc`

### Fixed
- Desktop retry counter stuck at 1/3 (reset bug in `start_desktop()`)
- Multiple monitor tasks spawned on retry
- CLI `--url`/`--api-key` ignored by `main.py`
- Missing API key in backend subprocess
- Root endpoint 404 (now shows API info with links)
- Qt Quick Controls 2 style not applied on Windows (PySide6 6.11.1 missing plugin)

### Changed
- Project version bumped to 1.2.0
- README updated with current module status
- Roadmap updated with completed modules
- Config restructured with `ui:`, `voice:`, `network:` sections

### Removed
- Duplicate `heartbeat_interval_seconds` and `graceful_shutdown_timeout_seconds` in config
- Deprecated `networking:` top-level key (replaced with `network:`)

---

## [1.1.0] - 2025-08-10

### Added
- Voice module: wake word (openwakeword), STT (faster-whisper), TTS (piper-tts)
- Network placeholders: WiFi, mDNS, AP, monitor
- Downloader tests: fixed HTTP test server, all 6 tests pass
- LSP support: pyrightconfig.json, type stubs for atlas.core.app
- 82 linting errors resolved across codebase

### Fixed
- Downloader test HTTP server infrastructure
- Circular imports in network module (loguru made optional)
- Type checking for TYPE_CHECKING imports

---

## [1.0.0] - 2025-08-01

### Added
- Runtime Core: application lifecycle, DI container, service registry, health monitoring, heartbeat, background tasks, signal handling
- Configuration system: Pydantic settings with YAML/env precedence
- Logging: structured logging setup
- CLI framework with Click
- API framework with FastAPI (routers, auth, CORS)
- AI providers framework: 30+ cloud providers + llama.cpp local
- Secrets management: keyring + encrypted file fallback
- Plugin core: registry, base classes
- 166 tests passing

---

## [0.1.0] - 2025-07-01

### Added
- Initial project structure
- Basic project layout and configuration