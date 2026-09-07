"""Unit tests for Voice AudioBackend abstraction."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from atlas.voice.audio import AudioBackend, AudioDevice, SounddeviceBackend
from atlas.voice.core import VoiceConfig, VoiceManager


class MockAudioBackend(AudioBackend):
    """Mock audio backend for testing VoiceManager without sound hardware."""

    def __init__(self, available: bool = True) -> None:
        self._available = available
        self.recorded_chunks: list[np.ndarray] = []
        self.played_audio: list[np.ndarray] = []

    def is_available(self) -> bool:
        return self._available

    def list_input_devices(self) -> list[AudioDevice]:
        return [
            AudioDevice(
                index=0,
                name="Mock Mic",
                max_input_channels=1,
                max_output_channels=0,
                default_sample_rate=16000.0,
                is_default_input=True,
            )
        ]

    def list_output_devices(self) -> list[AudioDevice]:
        return [
            AudioDevice(
                index=1,
                name="Mock Speaker",
                max_input_channels=0,
                max_output_channels=2,
                default_sample_rate=44100.0,
                is_default_output=True,
            )
        ]

    async def record(
        self,
        duration_seconds: float,
        sample_rate: int = 16000,
        channels: int = 1,
        device: int | str | None = None,
    ) -> np.ndarray:
        samples = int(duration_seconds * sample_rate)
        arr = np.zeros(samples, dtype=np.float32)
        self.recorded_chunks.append(arr)
        return arr

    async def play(
        self,
        audio: np.ndarray,
        sample_rate: int = 22050,
        device: int | str | None = None,
    ) -> None:
        self.played_audio.append(audio)

    async def open_input_stream(
        self,
        sample_rate: int,
        channels: int,
        blocksize: int,
        device: int | str | None = None,
    ):
        mock_stream = MagicMock()
        mock_stream.read.return_value = (np.zeros((blocksize, channels), dtype=np.float32), False)
        mock_stream.__enter__.return_value = mock_stream
        mock_stream.__exit__.return_value = None
        return mock_stream


class TestVoiceManagerWithBackend:
    """Test VoiceManager interaction with AudioBackend."""

    @pytest.mark.asyncio
    async def test_get_status_uses_wake_word_key(self):
        backend = MockAudioBackend(available=True)
        mgr = VoiceManager(audio_backend=backend)
        status = mgr.get_status()

        # Check key names
        assert "wake_word" in status
        assert "stt" in status
        assert "tts" in status
        assert "audio" in status
        assert status["audio"]["available"] is True
        assert status["audio"]["backend"] == "MockAudioBackend"
        assert status["audio"]["input_devices"] == 1
        assert status["audio"]["output_devices"] == 1

    @pytest.mark.asyncio
    async def test_listen_and_transcribe_calls_backend_record(self):
        backend = MockAudioBackend(available=True)
        mgr = VoiceManager(audio_backend=backend)
        mgr.stt.transcribe = AsyncMock(return_value="hello test")

        text = await mgr.listen_and_transcribe(duration_seconds=1.0)
        assert text == "hello test"
        assert len(backend.recorded_chunks) == 1

    @pytest.mark.asyncio
    async def test_speak_calls_backend_play(self):
        backend = MockAudioBackend(available=True)
        mgr = VoiceManager(audio_backend=backend)
        mgr.tts.synthesize = AsyncMock(return_value=np.array([0.1, 0.2], dtype=np.float32))

        ok = await mgr.speak("hello")
        assert ok is True
        assert len(backend.played_audio) == 1

    @pytest.mark.asyncio
    async def test_unavailable_audio_backend_fails_gracefully(self):
        backend = MockAudioBackend(available=False)
        mgr = VoiceManager(audio_backend=backend)

        assert await mgr.listen_and_transcribe(1.0) == ""
        assert await mgr.speak("hello") is False
        assert await mgr.listen_for_wake_word() is False


class TestSounddeviceBackend:
    """Test SounddeviceBackend behavior with and without sounddevice installed."""

    def test_audio_device_to_dict(self):
        dev = AudioDevice(
            index=0,
            name="Test",
            max_input_channels=2,
            max_output_channels=2,
            default_sample_rate=48000.0,
            is_default_input=True,
            is_default_output=False,
        )
        d = dev.to_dict()
        assert d["name"] == "Test"
        assert d["is_default_input"] is True
        assert d["is_default_output"] is False

    def test_is_available_when_sounddevice_missing(self):
        with patch("atlas.voice.audio._SOUNDDEVICE_AVAILABLE", False):
            backend = SounddeviceBackend()
            assert backend.is_available() is False
            assert backend.list_input_devices() == []
            assert backend.list_output_devices() == []
