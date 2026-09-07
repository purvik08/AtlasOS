"""Models routes for Atlas OS API."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from atlas.api.auth import require_auth
from atlas.runtime.application import AtlasApplication

logger = logging.getLogger(__name__)

router = APIRouter()


class ModelInfo(BaseModel):
    """Model information."""
    model_id: str
    display_name: str
    provider: str
    loaded: bool
    size_bytes: int
    description: str = ""


class LoadModelRequest(BaseModel):
    """Request to load a model."""
    model_id: str
    provider: str | None = None


class LoadModelResponse(BaseModel):
    """Response for model load/unload."""
    success: bool
    message: str


class DownloadModelRequest(BaseModel):
    """Request to download a model from Hugging Face or direct URL."""
    model_id: str
    url: str | None = None
    repo: str | None = None
    filename: str | None = None
    token: str | None = None
    overwrite: bool = False


class DownloadModelResponse(BaseModel):
    """Response for model download."""
    success: bool
    model_id: str
    path: str
    bytes_downloaded: int
    error: str | None = None


def get_app(request: Request) -> AtlasApplication:
    """Dependency to get AtlasApplication from request state."""
    return request.app.state.atlas_app


@router.get("/models", response_model=list[ModelInfo])
async def list_models(
    app: AtlasApplication = Depends(get_app),
    api_key: Any = Depends(require_auth),
    provider: str | None = Query(None, description="Filter by provider"),
    loaded_only: bool = Query(False, description="Show only loaded models"),
):
    """List all available models in the registry."""
    manager = app.container.resolve("ai_manager")
    # Rescan models dir to detect any new GGUF files added to disk
    manager.model_registry.scan(app.config.models_dir)
    models = manager.list_models()

    result = []
    for m in models:
        if provider and m.provider_name != provider:
            continue
        if loaded_only and not m.loaded:
            continue
        result.append(ModelInfo(
            model_id=m.model_id,
            display_name=m.display_name,
            provider=m.provider_name,
            loaded=m.loaded,
            size_bytes=m.size_bytes,
            description=m.description,
        ))

    return result


@router.get("/models/{model_id}", response_model=ModelInfo)
async def get_model(
    model_id: str,
    app: AtlasApplication = Depends(get_app),
    api_key: Any = Depends(require_auth),
) -> ModelInfo:
    """Get detailed model information."""
    manager = app.container.resolve("ai_manager")

    try:
        info = manager.model_registry.get(model_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found") from e

    return ModelInfo(
        model_id=info.model_id,
        display_name=info.display_name,
        provider=info.provider_name,
        loaded=info.loaded,
        size_bytes=info.size_bytes,
        description=info.description,
    )


@router.post("/models/{model_id}/load", response_model=LoadModelResponse)
async def load_model(
    model_id: str,
    request: LoadModelRequest,
    app: AtlasApplication = Depends(get_app),
    api_key: Any = Depends(require_auth),
) -> LoadModelResponse:
    """Load a model into memory."""
    manager = app.container.resolve("ai_manager")

    try:
        await manager.load_model(model_id, provider_name=request.provider)
        return LoadModelResponse(success=True, message=f"Model '{model_id}' loaded successfully")
    except Exception as e:
        logger.warning("Failed to load model %s: %s", model_id, e)
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/models/{model_id}/unload", response_model=LoadModelResponse)
async def unload_model(
    model_id: str,
    request: LoadModelRequest,
    app: AtlasApplication = Depends(get_app),
    api_key: Any = Depends(require_auth),
) -> LoadModelResponse:
    """Unload a model from memory."""
    manager = app.container.resolve("ai_manager")

    try:
        await manager.unload_model(model_id, provider_name=request.provider)
        return LoadModelResponse(success=True, message=f"Model '{model_id}' unloaded successfully")
    except Exception as e:
        logger.warning("Failed to unload model %s: %s", model_id, e)
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/models/download", response_model=DownloadModelResponse)
async def download_model(
    request: DownloadModelRequest,
    app: AtlasApplication = Depends(get_app),
    api_key: Any = Depends(require_auth),
) -> DownloadModelResponse:
    """Download a model from Hugging Face or direct URL into models_dir."""
    manager = app.container.resolve("ai_manager")

    if not request.url and not request.repo:
        raise HTTPException(status_code=400, detail="Provide 'url' or 'repo' to download.")

    if request.repo and not request.filename:
        raise HTTPException(status_code=400, detail="'filename' is required when downloading from a Hugging Face repo.")

    try:
        if request.repo:
            res = await manager.downloader.download_from_huggingface(
                repo_id=request.repo,
                filename=request.filename,
                token=request.token,
                overwrite=request.overwrite,
            )
        else:
            res = await manager.download_model(
                model_id=request.model_id,
                source_url=request.url,
                overwrite=request.overwrite,
            )

        # Rescan models directory so newly downloaded model appears in registry
        manager.model_registry.scan(app.config.models_dir)

        return DownloadModelResponse(
            success=res.success,
            model_id=request.model_id,
            path=str(res.path) if res.path else "",
            bytes_downloaded=res.bytes_downloaded,
            error=res.error,
        )
    except Exception as exc:
        logger.exception("Model download failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/models/{model_id}")
async def delete_model(
    model_id: str,
    delete_file: bool = Query(False, description="Also delete GGUF file from disk if local"),
    app: AtlasApplication = Depends(get_app),
    api_key: Any = Depends(require_auth),
) -> dict[str, Any]:
    """Remove a model from registry and optionally delete the file from disk."""
    manager = app.container.resolve("ai_manager")

    try:
        info = manager.model_registry.get(model_id)
        # Unload if currently loaded
        if info.loaded:
            await manager.unload_model(model_id)

        # Unregister from registry
        manager.model_registry.unregister(model_id)

        # If local and delete_file requested, delete the GGUF file
        file_deleted = False
        if delete_file and info.provider_name == "llama_cpp":
            model_file = Path(app.config.models_dir) / f"{model_id}.gguf"
            if model_file.exists():
                model_file.unlink()
                file_deleted = True

        return {
            "success": True,
            "model_id": model_id,
            "file_deleted": file_deleted,
            "message": f"Model '{model_id}' removed.",
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/models/scan")
async def scan_models(
    app: AtlasApplication = Depends(get_app),
    api_key: Any = Depends(require_auth),
) -> dict[str, Any]:
    """Rescan the models directory and refresh ModelRegistry."""
    manager = app.container.resolve("ai_manager")
    manager.model_registry.scan(app.config.models_dir)
    return {
        "success": True,
        "count": len(manager.model_registry),
        "models": [m.model_id for m in manager.list_models()],
    }