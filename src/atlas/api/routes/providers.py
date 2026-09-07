"""Providers routes for Atlas OS API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from atlas.api.auth import require_auth
from atlas.runtime.application import AtlasApplication

router = APIRouter()


class ProviderInfo(BaseModel):
    """Provider information."""
    name: str
    role: str
    description: str
    available: bool
    models_count: int


class ProviderHealth(BaseModel):
    """Provider health response."""
    provider_name: str
    status: str
    loaded_models: list[str]
    message: str


def get_app(request: Request) -> AtlasApplication:
    """Dependency to get AtlasApplication from request state."""
    return request.app.state.atlas_app


@router.get("/providers", response_model=list[ProviderInfo])
async def list_providers(
    app: AtlasApplication = Depends(get_app),
    api_key: str = Depends(require_auth),
):
    """List all registered AI providers."""
    manager = app.container.resolve("ai_manager")
    provider_infos = manager.list_providers()
    
    result = []
    for p_info in provider_infos:
        # Get the actual provider instance to call list_models
        provider = manager.router.get(p_info.name)
        models = await provider.list_models()
        result.append(ProviderInfo(
            name=provider.name,
            role=provider.role.value,
            description=provider.description,
            available=True,
            models_count=len(models),
        ))
    
    return result


@router.get("/providers/{provider_name}", response_model=ProviderInfo)
async def get_provider(
    provider_name: str,
    app: AtlasApplication = Depends(get_app),
    api_key: str = Depends(require_auth),
) -> ProviderInfo:
    """Get provider details."""
    manager = app.container.resolve("ai_manager")
    
    try:
        provider = manager.router.get(provider_name)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' not found") from e
    
    models = await provider.list_models()
    return ProviderInfo(
        name=provider.name,
        role=provider.role.value,
        description=provider.description,
        available=True,
        models_count=len(models),
    )


@router.get("/providers/{provider_name}/health", response_model=ProviderHealth)
async def provider_health(
    provider_name: str,
    app: AtlasApplication = Depends(get_app),
    api_key: str = Depends(require_auth),
) -> ProviderHealth:
    """Get provider health status."""
    manager = app.container.resolve("ai_manager")
    
    try:
        health = await manager.provider_health(provider_name)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    
    return ProviderHealth(
        provider_name=health.provider_name,
        status=health.status.value,
        loaded_models=health.loaded_models,
        message=health.message,
    )


@router.get("/providers/{provider_name}/models")
async def provider_models(
    provider_name: str,
    app: AtlasApplication = Depends(get_app),
    api_key: str = Depends(require_auth),
) -> dict[str, Any]:
    """List models for a specific provider."""
    manager = app.container.resolve("ai_manager")
    
    try:
        provider = manager.router.get(provider_name)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' not found") from e
    
    models = await provider.list_models()
    return {
        "provider": provider_name,
        "models": [
            {
                "model_id": m.model_id,
                "display_name": m.display_name,
                "loaded": m.loaded,
                "size_bytes": m.size_bytes,
            }
            for m in models
        ],
    }