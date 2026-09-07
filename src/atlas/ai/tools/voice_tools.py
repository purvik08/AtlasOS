"""Voice and audio tools for Atlas OS AI."""

from __future__ import annotations

import logging
from typing import Any

from atlas.ai.tools.base import BaseTool, ToolPermissionLevel, ToolResult
from atlas.voice.core import VoiceManager

logger = logging.getLogger(__name__)


class GetVoiceStatusTool(BaseTool):
    """Tool to inspect wake word, STT, TTS, and microphone availability."""

    name = "get_voice_status"
    description = "Get status of the voice interaction subsystem, speech-to-text, text-to-speech, and microphones."
    permission_level = ToolPermissionLevel.READ_ONLY
    parameters = []

    def __init__(self, voice_manager: VoiceManager | None = None) -> None:
        self._voice_manager = voice_manager

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            vm = self._voice_manager or VoiceManager()
            status = vm.get_status()
            return ToolResult(success=True, data=status)
        except Exception as exc:
            return ToolResult(success=False, data=None, error=str(exc))
