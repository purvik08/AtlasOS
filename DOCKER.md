# Docker Deployment for Atlas OS

This directory contains Docker configurations to containerize Atlas OS as a microservice.

## Quick Start

### Production (Minimal)
```bash
docker compose up -d
```

This builds and runs the API server on port 8000 with minimal dependencies:
- **Image:** `atlasos-atlas-api:latest` (~500MB)
- **Base:** Python 3.12-slim + core dependencies only
- **Note:** Voice, sentence-transformers, and other optional features are disabled

The container auto-restarts and includes a health check.

### Development (Full Features)
```bash
docker compose -f docker-compose.dev.yml up -d
```

This includes all optional dependencies for development:
- numpy, scipy, sentence-transformers
- sounddevice, openwakeword, faster-whisper, piper-tts
- Live code reloading (mount `/app/src`)
- Debug logging enabled

## Files

- **Dockerfile** — Multi-stage build for production (minimal footprint)
- **Dockerfile.dev** — Development build with all extras + hot-reload
- **docker-compose.yml** — Production service definition
- **docker-compose.dev.yml** — Development service definition
- **.dockerignore** — Excludes unnecessary files from build context

## Architecture

### Multi-Stage Build (Production)
1. **Builder stage:** Installs build tools, creates wheel from source
2. **Runtime stage:** Copies wheel, installs minimal dependencies, runs API

**Result:** ~500MB image, ~30s startup.

### Development
- Mounts source code for hot-reload
- Installs all optional dependencies
- Verbose logging

## Volumes

| Mount | Purpose |
|-------|---------|
| `atlas-data` | Persists users, API keys, memories, runtime state |
| `atlas-models` | Caches LLM models (empty by default) |
| `atlas-logs` | Application logs |

## Environment Variables

Set in `docker-compose.yml` or via `.env`:

```bash
ATLAS_LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR
ATLAS_ENVIRONMENT=production      # development, production, testing
PYTHONUNBUFFERED=1               # Don't buffer Python output
```

## API Health Check

The container includes an automatic health check:

```bash
docker compose exec atlas-api curl http://127.0.0.1:8000/
```

Expected response:
```json
{"message": "Atlas OS API", "health": "/v1/health", "docs": "/docs", "ui": "/ui"}
```

## Known Limitations (Production)

The production image excludes optional dependencies. To use voice features or sentence-transformers embeddings, run the dev compose or extend the Dockerfile.

## Next Steps

- **Push to registry:** `docker tag atlas-os:latest your-registry/atlas-os:latest && docker push ...`
- **Kubernetes:** Use docker-compose manifest or create Helm chart
- **CI/CD:** Add GitHub Actions workflow to build and push on push

## Troubleshooting

### Container won't start
```bash
docker compose logs -f
```

### Port already in use
```bash
docker compose down -v
# Or change port in docker-compose.yml
```

### Models don't persist
Ensure `atlas-models` volume is mounted and writable.

### Memory limits
Adjust in docker-compose.yml:
```yaml
services:
  atlas-api:
    deploy:
      resources:
        limits:
          memory: 4G
```
