"""Audio backend abstraction for Atlas OS VoiceService.

Keeps VoiceService hardware-independent:
    VoiceManager
        ↓
    AudioBackend (ABC)
        ↓
    SounddeviceBackend     — sounddevice / PortAudio
        ↓
    Linux audio subsystem  — PipeWire / PulseAudio / ALSA

This abstraction means alternative audio backends (e.g. ALSA-direct,
PipeWire native) can be plugged in without changing VoiceManager.

Missing audio dependencies fail gracefully — ``is_available()`` returns
False and operations log clear error messages.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional: sounddevice
# ---------------------------------------------------------------------------
try:
    import sounddevice as _sd
    _SOUNDDEVICE_AVAILABLE = True
except ImportError:
    _sd = None  # type: ignore[assignment]
    _SOUNDDEVICE_AVAILABLE = False


@dataclass
class AudioDevice:
    """Represents an audio input or output device."""
    index: int
    name: str
    max_input_channels: int
    max_output_channels: int
    default_sample_rate: float
    is_default_input: bool = False
    is_default_output: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "name": self.name,
            "max_input_channels": self.max_input_channels,
            "max_output_channels": self.max_output_channels,
            "default_sample_rate": self.default_sample_rate,
            "is_default_input": self.is_default_input,
            "is_default_output": self.is_default_output,
        }


class AudioBackend(ABC):
    """Abstract audio backend interface.

    Implementations must not raise on import; missing dependencies must be
    reported via ``is_available() == False``.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this backend can provide audio I/O on this system."""

    @abstractmethod
    def list_input_devices(self) -> list[AudioDevice]:
        """Return available audio input (microphone) devices."""

    @abstractmethod
    def list_output_devices(self) -> list[AudioDevice]:
        """Return available audio output (speaker) devices."""

    @abstractmethod
    async def record(
        self,
        duration_seconds: float,
        sample_rate: int = 16000,
        channels: int = 1,
        device: int | str | None = None,
    ) -> np.ndarray:
        """Record audio from the microphone.

        Args:
            duration_seconds: How long to record.
            sample_rate:      Sample rate in Hz.
            channels:         Number of channels (1 = mono).
            device:           Device index or name; uses default if None.

        Returns:
            Float32 numpy array of shape ``(samples,)`` or ``(samples, channels)``.
        """

    @abstractmethod
    async def play(
        self,
        audio: np.ndarray,
        sample_rate: int = 22050,
        device: int | str | None = None,
    ) -> None:
        """Play audio through the speaker.

        Args:
            audio:       Float32 numpy array.
            sample_rate: Sample rate in Hz.
            device:      Device index or name; uses default if None.
        """

    @abstractmethod
    async def open_input_stream(
        self,
        sample_rate: int,
        channels: int,
        blocksize: int,
        device: int | str | None = None,
    ) -> Any:
        """Return a context-manager audio input stream for continuous capture."""


class SounddeviceBackend(AudioBackend):
    """Audio backend using sounddevice / PortAudio.

    Works with PipeWire, PulseAudio, and ALSA on Linux.
    Recommended for Raspberry Pi 5 running modern Raspberry Pi OS.
    """

    def __init__(self) -> None:
        self._cached_devices: list[dict[str, Any]] | None = None
        self._cached_default: tuple[int, int] | None = None
        self._last_scan_time: float = 0.0
        self._cache_ttl: float = 5.0

    def _get_devices(self) -> tuple[list[dict[str, Any]], tuple[int, int]]:
        """Query sounddevice devices with TTL caching."""
        import time
        now = time.monotonic()
        if (
            self._cached_devices is not None
            and self._cached_default is not None
            and (now - self._last_scan_time) < self._cache_ttl
        ):
            return self._cached_devices, self._cached_default

        if not _SOUNDDEVICE_AVAILABLE or _sd is None:
            return [], (-1, -1)

        try:
            devs = list(_sd.query_devices())
            defaults = tuple(_sd.default.device) if hasattr(_sd.default, "device") else (-1, -1)
            self._cached_devices = devs
            self._cached_default = defaults
            self._last_scan_time = now
            return devs, defaults
        except Exception:
            return [], (-1, -1)

    def is_available(self) -> bool:
        """Return True if sounddevice is installed and audio devices exist."""
        if not _SOUNDDEVICE_AVAILABLE:
            return False
        devs, _ = self._get_devices()
        return len(devs) > 0

    def list_input_devices(self) -> list[AudioDevice]:
        """List microphone/input devices."""
        if not _SOUNDDEVICE_AVAILABLE:
            return []
        try:
            devices, defaults = self._get_devices()
            default_in = defaults[0] if defaults else -1
            result: list[AudioDevice] = []
            for idx, dev in enumerate(devices):
                if dev.get("max_input_channels", 0) > 0:
                    result.append(AudioDevice(
                        index=idx,
                        name=dev.get("name", f"Input {idx}"),
                        max_input_channels=dev.get("max_input_channels", 1),
                        max_output_channels=dev.get("max_output_channels", 0),
                        default_sample_rate=dev.get("default_samplerate", 16000.0),
                        is_default_input=(idx == default_in),
                    ))
            return result
        except Exception as exc:
            logger.warning("Failed to list input devices: %s", exc)
            return []

    def list_output_devices(self) -> list[AudioDevice]:
        """List speaker/output devices."""
        if not _SOUNDDEVICE_AVAILABLE:
            return []
        try:
            devices, defaults = self._get_devices()
            default_out = defaults[1] if defaults and len(defaults) > 1 else -1
            result: list[AudioDevice] = []
            for idx, dev in enumerate(devices):
                if dev.get("max_output_channels", 0) > 0:
                    result.append(AudioDevice(
                        index=idx,
                        name=dev.get("name", f"Output {idx}"),
                        max_input_channels=dev.get("max_input_channels", 0),
                        max_output_channels=dev.get("max_output_channels", 2),
                        default_sample_rate=dev.get("default_samplerate", 22050.0),
                        is_default_output=(idx == default_out),
                    ))
            return result
        except Exception as exc:
            logger.warning("Failed to list output devices: %s", exc)
            return []

    async def record(
        self,
        duration_seconds: float,
        sample_rate: int = 16000,
        channels: int = 1,
        device: int | str | None = None,
    ) -> np.ndarray:
        """Record from microphone using sounddevice."""
        if not _SOUNDDEVICE_AVAILABLE:
            logger.error(
                "sounddevice not available. "
                "Install with: pip install sounddevice"
            )
            return np.array([], dtype=np.float32)

        sample_count = int(sample_rate * duration_seconds)
        try:
            kwargs: dict[str, Any] = {
                "samplerate": sample_rate,
                "channels": channels,
                "dtype": "float32",
            }
            if device is not None:
                kwargs["device"] = device

            recording = _sd.rec(sample_count, **kwargs)
            await asyncio.to_thread(_sd.wait)
            return recording.flatten() if channels == 1 else recording
        except Exception as exc:
            logger.error("Recording failed: %s", exc)
            return np.array([], dtype=np.float32)

    async def play(
        self,
        audio: np.ndarray,
        sample_rate: int = 22050,
        device: int | str | None = None,
    ) -> None:
        """Play audio through speaker using sounddevice."""
        if not _SOUNDDEVICE_AVAILABLE:
            logger.error("sounddevice not available; cannot play audio")
            return
        if len(audio) == 0:
            return
        try:
            kwargs: dict[str, Any] = {"samplerate": sample_rate}
            if device is not None:
                kwargs["device"] = device
            _sd.play(audio, **kwargs)
            await asyncio.to_thread(_sd.wait)
        except Exception as exc:
            logger.error("Audio playback failed: %s", exc)

    async def open_input_stream(
        self,
        sample_rate: int,
        channels: int,
        blocksize: int,
        device: int | str | None = None,
    ) -> Any:
        """Return a sounddevice InputStream for continuous capture."""
        if not _SOUNDDEVICE_AVAILABLE:
            raise RuntimeError(
                "sounddevice not available. Install with: pip install sounddevice"
            )
        kwargs: dict[str, Any] = {
            "samplerate": sample_rate,
            "channels": channels,
            "dtype": "float32",
            "blocksize": blocksize,
        }
        if device is not None:
            kwargs["device"] = device
        return _sd.InputStream(**kwargs)
