"""Plugin management routes for Atlas OS API."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from atlas.api.auth import require_auth
from atlas.plugins.core import PluginManager
from atlas.runtime.application import AtlasApplication

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/plugins", tags=["plugins"])


def get_app(request: Request) -> AtlasApplication:
    return request.app.state.atlas_app


@router.get("")
async def list_plugins(
    app: AtlasApplication = Depends(get_app),
    api_key: Any = Depends(require_auth),
) -> dict[str, Any]:
    """List all discovered plugins, enabled states, and permissions."""
    pm = PluginManager(plugins_dir=app.config.plugins_dir)
    plugins = pm.discover()

    return {
        "count": len(plugins),
        "plugins": [
            {
                "name": p.manifest.name,
                "version": p.manifest.version,
                "description": p.manifest.description,
                "author": p.manifest.author,
                "enabled": p.enabled,
                "loaded": p.loaded,
                "permissions": p.manifest.permissions,
                "error": p.error,
            }
            for p in plugins.values()
        ],
    }


@router.post("/{plugin_name}/enable")
async def enable_plugin(
    plugin_name: str,
    app: AtlasApplication = Depends(get_app),
    api_key: Any = Depends(require_auth),
) -> dict[str, Any]:
    """Enable a plugin."""
    pm = PluginManager(plugins_dir=app.config.plugins_dir)
    pm.discover()
    ok = pm.enable(plugin_name)
    if not ok:
        raise HTTPException(status_code=400, detail=f"Failed to enable plugin '{plugin_name}'.")
    return {"success": True, "message": f"Plugin '{plugin_name}' enabled."}


@router.post("/{plugin_name}/disable")
async def disable_plugin(
    plugin_name: str,
    app: AtlasApplication = Depends(get_app),
    api_key: Any = Depends(require_auth),
) -> dict[str, Any]:
    """Disable a plugin."""
    pm = PluginManager(plugins_dir=app.config.plugins_dir)
    pm.discover()
    ok = pm.disable(plugin_name)
    if not ok:
        raise HTTPException(status_code=400, detail=f"Failed to disable plugin '{plugin_name}'.")
    return {"success": True, "message": f"Plugin '{plugin_name}' disabled."}
