"""System and health check routes.

Auth structure:
- /health, /ready  — unauthenticated (public liveness probes)
- /status, /metrics — API key auth (existing behaviour preserved)
- /shutdown, /reboot, /config — admin JWT required (v1.3.0 new protection)
"""

from __future__ import annotations

import platform
import socket
import sys
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from atlas.api.auth import require_auth
from atlas.auth.middleware import require_admin
from atlas.auth.models import User
from atlas.runtime.application import AtlasApplication

router = APIRouter()


def get_app(request: Request) -> AtlasApplication:
    """Dependency to get AtlasApplication from request state."""
    return request.app.state.atlas_app


def _get_primary_ip() -> str:
    """Return the primary LAN-facing IP address, falling back to localhost."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


# ---------------------------------------------------------------------------
# Public endpoints (unauthenticated)
# ---------------------------------------------------------------------------

@router.get("/health")
async def health_check(app: AtlasApplication = Depends(get_app)) -> dict[str, Any]:
    """Health check endpoint — no auth required."""
    report = app.health_monitor.latest_report
    return {
        "status": report.status.value,
        "services": [
            {"name": s.name, "status": s.status.value, "message": s.message}
            for s in report.services
        ],
        "timestamp": report.generated_at,
    }


@router.get("/ready")
async def readiness_check(app: AtlasApplication = Depends(get_app)) -> dict[str, str]:
    """Readiness check — no auth required."""
    if app.state.value != "running":
        raise HTTPException(status_code=503, detail="Service not ready")
    return {"status": "ready"}


@router.get("/system/info")
async def system_info(
    app: AtlasApplication = Depends(get_app),
    api_key: str = Depends(require_auth),
) -> dict[str, Any]:
    """Return dashboard-friendly system, runtime, and resource information."""
    import psutil

    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    boot_time = psutil.boot_time()

    temperature_c: float | None = None
    try:
        temps = psutil.sensors_temperatures()
        for readings in temps.values():
            if readings:
                temperature_c = float(readings[0].current)
                break
    except (AttributeError, OSError):
        temperature_c = None

    return {
        "app_name": app.config.app_name,
        "environment": app.config.environment,
        "runtime_state": app.state.value,
        "uptime_seconds": app.uptime_seconds or max(0.0, time.time() - boot_time),
        "hostname": socket.gethostname(),
        "ip_address": _get_primary_ip(),
        "os": platform.platform(),
        "platform": platform.system(),
        "arch": platform.machine(),
        "python": sys.version.split()[0],
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "cpu_count": psutil.cpu_count(logical=True),
        "memory_percent": mem.percent,
        "memory_used_gb": round(mem.used / (1024**3), 2),
        "memory_total_gb": round(mem.total / (1024**3), 2),
        "disk_percent": disk.percent,
        "disk_used_gb": round(disk.used / (1024**3), 2),
        "disk_total_gb": round(disk.total / (1024**3), 2),
        "temperature_c": temperature_c,
        "registered_services": len(app.registry.all()),
        "active_tasks": len(app.tasks._tasks),
        "config": {
            "data_dir": app.config.data_dir,
            "models_dir": app.config.models_dir,
            "plugins_dir": app.config.plugins_dir,
            "log_level": app.config.log_level,
        },
    }


# ---------------------------------------------------------------------------
# API-key protected endpoints (existing behaviour preserved)
# ---------------------------------------------------------------------------

@router.get("/status")
async def runtime_status(
    app: AtlasApplication = Depends(get_app),
    api_key: str = Depends(require_auth),
) -> dict[str, Any]:
    """Detailed runtime status (requires API key auth)."""
    return {
        "state": app.state.value,
        "uptime_seconds": app.uptime_seconds,
        "registered_services": len(app.registry.all()),
        "active_tasks": len(app.tasks._tasks),
        "config": {
            "app_name": app.config.app_name,
            "environment": app.config.environment,
            "log_level": app.config.log_level,
        },
    }


@router.get("/metrics")
async def runtime_metrics(
    app: AtlasApplication = Depends(get_app),
    api_key: str = Depends(require_auth),
) -> dict[str, Any]:
    """Runtime metrics (requires API key auth)."""
    import psutil

    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()

    return {
        "cpu_percent": cpu,
        "memory": {
            "total_bytes": mem.total,
            "available_bytes": mem.available,
            "used_bytes": mem.used,
            "percent": mem.percent,
        },
        "uptime_seconds": app.uptime_seconds,
    }


# ---------------------------------------------------------------------------
# Admin-only endpoints (JWT + admin role required)
# Protects dangerous operations: shutdown, reboot, config changes, updates.
# ---------------------------------------------------------------------------

@router.post("/shutdown")
async def system_shutdown(
    app: AtlasApplication = Depends(get_app),
    admin: User = Depends(require_admin),
) -> dict[str, str]:
    """Gracefully shut down Atlas OS (admin only)."""
    import asyncio
    asyncio.create_task(app.stop())
    return {"detail": f"Shutdown initiated by {admin.username}"}


@router.post("/reboot")
async def system_reboot(
    admin: User = Depends(require_admin),
) -> dict[str, str]:
    """Reboot the system (admin only)."""
    import asyncio

    try:
        await asyncio.create_subprocess_exec("sudo", "reboot")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Reboot failed: {exc}") from exc
    return {"detail": f"Reboot initiated by {admin.username}"}


@router.get("/config")
async def get_config(
    app: AtlasApplication = Depends(get_app),
    admin: User = Depends(require_admin),
) -> dict[str, Any]:
    """Return current configuration (admin only)."""
    cfg = app.config
    return {
        "app_name": cfg.app_name,
        "environment": cfg.environment,
        "log_level": cfg.log_level,
        "data_dir": cfg.data_dir,
        "models_dir": cfg.models_dir,
        "plugins_dir": cfg.plugins_dir,
    }
