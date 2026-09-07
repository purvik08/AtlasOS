"""Atlas API module."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI
    from atlas.runtime.application import AtlasApplication

# AtlasSDK is a pure httpx-based client — safe to import in any context
# (desktop subprocess, CLI, backend server). It has no fastapi dependency.
from atlas.api.sdk import AtlasSDK

_atlas_app = None


def get_atlas_app():
    """Get the global AtlasApplication instance."""
    return _atlas_app


def set_atlas_app(app) -> None:
    """Set the global AtlasApplication instance."""
    global _atlas_app
    _atlas_app = app


def create_api_app(app: "AtlasApplication") -> "FastAPI":
    """Create FastAPI app with all routes."""
    from contextlib import asynccontextmanager
    from pathlib import Path
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from atlas.api.auth import AuthManager, set_auth_manager
    from atlas.api.routes import (
        auth_router,
        chat_router,
        memory_router,
        models_router,
        network_router,
        openai_router,
        plugins_router,
        providers_router,
        rag_router,
        sessions_router,
        system_router,
        terminal_router,
        voice_router,
    )
    from atlas.runtime.application import AtlasApplication

    @asynccontextmanager
    async def lifespan(app_instance: FastAPI):
        from atlas.secrets import sync_secrets_to_config
        sync_secrets_to_config(app.config)
        if app.container.is_registered("ai_manager"):
            ai_manager = app.container.resolve("ai_manager")
            await ai_manager.start()
        try:
            yield
        finally:
            if app.container.is_registered("ai_manager"):
                ai_manager = app.container.resolve("ai_manager")
                await ai_manager.stop()

    fastapi_app = FastAPI(
        title="Atlas OS API",
        version="0.1.0",
        description="Local AI Edge Operating System API",
        lifespan=lifespan,
    )

    # CORS
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static assets for Web UI if present
    _web_dir = Path(__file__).parent / "web"
    if _web_dir.exists():
        fastapi_app.mount("/static", StaticFiles(directory=str(_web_dir)), name="static")

    # Store app reference for dependency injection AND state access
    set_atlas_app(app)
    fastapi_app.state.atlas_app = app

    # Set API key auth manager
    auth_manager = AuthManager(app.config)
    set_auth_manager(auth_manager)
    fastapi_app.state.auth_manager = auth_manager

    # Set JWT/local-user auth manager
    from atlas.auth.manager import LocalAuthManager
    data_dir = getattr(app.config, "data_dir", "./data")
    local_auth = LocalAuthManager(data_dir)
    default_password = local_auth.ensure_default_admin()
    if default_password:
        import logging
        logging.getLogger(__name__).warning(
            "First-run: default admin created. "
            "Login at POST /v1/auth/login with username=admin password=%s",
            default_password,
        )
    fastapi_app.state.local_auth_manager = local_auth

    # Include all API routers
    fastapi_app.include_router(auth_router, prefix="/v1")
    fastapi_app.include_router(system_router, prefix="/v1")
    fastapi_app.include_router(models_router, prefix="/v1")
    fastapi_app.include_router(providers_router, prefix="/v1")
    fastapi_app.include_router(chat_router, prefix="/v1")
    fastapi_app.include_router(openai_router, prefix="/v1")
    fastapi_app.include_router(sessions_router, prefix="/v1")
    fastapi_app.include_router(network_router, prefix="/v1")
    fastapi_app.include_router(voice_router, prefix="/v1")
    fastapi_app.include_router(memory_router, prefix="/v1")
    fastapi_app.include_router(rag_router, prefix="/v1")
    fastapi_app.include_router(plugins_router, prefix="/v1")
    fastapi_app.include_router(terminal_router, prefix="/v1")

    @fastapi_app.get("/", response_class=HTMLResponse)
    async def root(request: Request):
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            html_file = Path(__file__).parent / "web" / "index.html"
            if html_file.exists():
                return HTMLResponse(html_file.read_text(encoding="utf-8"))
        return JSONResponse({"message": "Atlas OS API", "health": "/v1/health", "docs": "/docs", "ui": "/ui"})

    @fastapi_app.get("/ui", response_class=HTMLResponse)
    async def web_ui():
        html_file = Path(__file__).parent / "web" / "index.html"
        if html_file.exists():
            return HTMLResponse(html_file.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>Atlas OS Web UI not found</h1>", status_code=404)

    return fastapi_app


def run_api_server() -> None:
    """Run the API server (lazy import to avoid circular dependency)."""
    from atlas.api.server import main
    main()


def __getattr__(name: str):
    server_side = {"AuthManager", "get_auth_manager", "require_auth", "set_auth_manager"}
    if name in server_side:
        import importlib
        auth_mod = importlib.import_module("atlas.api.auth")
        return getattr(auth_mod, name)
    raise AttributeError(f"module 'atlas.api' has no attribute {name!r}")


__all__ = [
    "AuthManager",
    "get_auth_manager",
    "require_auth",
    "set_auth_manager",
    "AtlasSDK",
    "run_api_server",
    "get_atlas_app",
    "set_atlas_app",
    "create_api_app",
]