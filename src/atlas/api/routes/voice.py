"""Voice subsystem routes for Atlas OS API."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from atlas.api.auth import require_auth
from atlas.runtime.application import AtlasApplication
from atlas.voice.core import VoiceManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])


class SpeakRequest(BaseModel):
    text: str


def get_app(request: Request) -> AtlasApplication:
    return request.app.state.atlas_app


def get_voice_manager(app: AtlasApplication = Depends(get_app)) -> VoiceManager:
    if "voice_manager" in app.container:
        return app.container.resolve("voice_manager")
    vm = VoiceManager()
    app.container.register_instance("voice_manager", vm)
    return vm


@router.get("/status")
async def voice_status(
    vm: VoiceManager = Depends(get_voice_manager),
    api_key: Any = Depends(require_auth),
) -> dict[str, Any]:
    """Get voice engine status (wake-word, STT, TTS, audio devices)."""
    return vm.get_status()


@router.get("/devices")
async def list_audio_devices(
    vm: VoiceManager = Depends(get_voice_manager),
    api_key: Any = Depends(require_auth),
) -> dict[str, Any]:
    """List available input microphones and output audio devices."""
    inputs = vm.list_input_devices()
    outputs = vm.list_output_devices()

    return {
        "inputs": [
            {
                "index": d.index,
                "name": d.name,
                "channels": d.max_input_channels,
                "default_sample_rate": d.default_sample_rate,
                "is_default": d.is_default_input,
            }
            for d in inputs
        ],
        "outputs": [
            {
                "index": d.index,
                "name": d.name,
                "channels": d.max_output_channels,
                "default_sample_rate": d.default_sample_rate,
                "is_default": d.is_default_output,
            }
            for d in outputs
        ],
    }


@router.post("/speak")
async def speak_text(
    request: SpeakRequest,
    vm: VoiceManager = Depends(get_voice_manager),
    api_key: Any = Depends(require_auth),
) -> dict[str, Any]:
    """Synthesize and play speech via Piper TTS."""
    try:
        ok = await vm.speak(request.text)
        return {"success": ok, "message": "Speech completed" if ok else "TTS unavailable"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

