"""Voice interaction core for Atlas OS.

Provides wake word detection, speech-to-text, and text-to-speech integration.

Audio I/O is handled through an AudioBackend abstraction so VoiceManager
is not tightly coupled to sounddevice/PortAudio/PipeWire/ALSA.

Architecture:
    VoiceManager
        ↓
    AudioBackend (ABC)       ← injected; defaults to SounddeviceBackend
        ↓
    sounddevice / PortAudio
        ↓
    Linux audio: PipeWire / ALSA
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from atlas.voice.audio import AudioBackend, AudioDevice, SounddeviceBackend

logger = logging.getLogger(__name__)

# Optional imports - graceful degradation
try:
    from openwakeword.model import Model
    _OPENWAKEWORD_AVAILABLE = True
except ImportError:
    _OPENWAKEWORD_AVAILABLE = False

try:
    from faster_whisper import WhisperModel
    _FASTER_WHISPER_AVAILABLE = True
except ImportError:
    _FASTER_WHISPER_AVAILABLE = False

try:
    import piper
    _PIPER_AVAILABLE = True
except ImportError:
    _PIPER_AVAILABLE = False


@dataclass
class VoiceConfig:
    """Voice system configuration."""
    # Wake word
    wake_word_model: str = "alexa"
    wake_word_threshold: float = 0.5
    wake_word_sensitivity: float = 0.5

    # Audio
    sample_rate: int = 16000
    channels: int = 1
    chunk_duration_ms: int = 80
    vad_threshold: float = 0.5

    # Device selection (None = use system default)
    input_device: int | str | None = None
    output_device: int | str | None = None

    # STT (faster-whisper)
    stt_model: str = "base.en"
    stt_device: str = "cpu"
    stt_compute_type: str = "int8"
    stt_language: str = "en"

    # TTS (piper)
    tts_model: str = "en_US-lessac-medium"
    tts_speaker: str = ""
    tts_length_scale: float = 1.0
    tts_noise_scale: float = 0.667
    tts_noise_w: float = 0.8


class WakeWordDetector:
    """Wake word detection using openWakeWord."""

    def __init__(self, config: VoiceConfig) -> None:
        self.config = config
        self._model: Any = None
        self._running = False

    async def initialize(self) -> bool:
        """Initialize the wake word model."""
        if not _OPENWAKEWORD_AVAILABLE:
            logger.warning("openWakeWord not available. Install with: pip install openwakeword")
            return False

        try:
            self._model = Model(
                wakeword_models=[self.config.wake_word_model],
                inference_framework="onnx",
            )
            logger.info("Wake word detector initialized: %s", self.config.wake_word_model)
            return True
        except Exception:
            logger.exception("Failed to initialize wake word detector")
            return False

    async def detect(self, audio_chunk: np.ndarray) -> bool:
        """Detect wake word in audio chunk."""
        if not self._model:
            return False

        try:
            prediction = self._model.predict(audio_chunk)
            score = prediction.get(self.config.wake_word_model, 0.0)
            return score >= self.config.wake_word_threshold
        except Exception:
            return False

    async def start(self) -> None:
        """Start wake word detection."""
        self._running = True

    async def stop(self) -> None:
        """Stop wake word detection."""
        self._running = False


class SpeechToText:
    """Speech-to-text using faster-whisper."""

    def __init__(self, config: VoiceConfig) -> None:
        self.config = config
        self._model: Any = None

    async def initialize(self) -> bool:
        """Initialize the Whisper model."""
        if not _FASTER_WHISPER_AVAILABLE:
            logger.warning("faster-whisper not available. Install with: pip install faster-whisper")
            return False

        try:
            self._model = WhisperModel(
                self.config.stt_model,
                device=self.config.stt_device,
                compute_type=self.config.stt_compute_type,
            )
            logger.info("STT model initialized: %s", self.config.stt_model)
            return True
        except Exception:
            logger.exception("Failed to initialize STT")
            return False

    async def transcribe(self, audio_data: np.ndarray) -> str:
        """Transcribe audio data to text."""
        if not self._model:
            return ""

        try:
            # Write audio to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
                self._write_wav(tmp_path, audio_data)

            try:
                segments, _ = self._model.transcribe(
                    tmp_path,
                    language=self.config.stt_language,
                    beam_size=5,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500),
                )
                text = " ".join(segment.text for segment in segments)
                return text.strip()
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        except Exception:
            logger.exception("Transcription failed")
            return ""

    def _write_wav(self, path: str, audio: np.ndarray) -> None:
        """Write numpy array as WAV file."""
        with wave.open(path, "wb") as wf:
            wf.setnchannels(self.config.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.config.sample_rate)
            # Convert float32 to int16
            audio_int16 = (audio * 32767).astype(np.int16)
            wf.writeframes(audio_int16.tobytes())


class TextToSpeech:
    """Text-to-speech using Piper."""

    def __init__(self, config: VoiceConfig) -> None:
        self.config = config
        self._voice: Any = None

    async def initialize(self) -> bool:
        """Initialize the Piper voice."""
        if not _PIPER_AVAILABLE:
            logger.warning("Piper not available. Install with: pip install piper-tts")
            return False

        try:
            # Download voice if needed
            voice_path = self._get_voice_path()
            if not voice_path.exists():
                await self._download_voice(voice_path)

            self._voice = piper.PiperVoice.load(voice_path)
            logger.info("TTS voice initialized: %s", self.config.tts_model)
            return True
        except Exception:
            logger.exception("Failed to initialize TTS")
            return False

    def _get_voice_path(self) -> Path:
        """Get path to Piper voice model."""
        # Check common locations
        paths = [
            Path.home() / ".local/share/piper" / f"{self.config.tts_model}.onnx",
            Path("/usr/share/piper-tts") / f"{self.config.tts_model}.onnx",
            Path.cwd() / "models" / "piper" / f"{self.config.tts_model}.onnx",
        ]
        for p in paths:
            if p.exists():
                return p
        return paths[0]

    async def _download_voice(self, path: Path) -> None:
        """Download Piper voice model."""
        path.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://github.com/rhasspy/piper/releases/download/v1.2.0/{self.config.tts_model}.onnx"
        logger.info("Downloading TTS voice from %s", url)

        import httpx
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                with path.open("wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)

    async def synthesize(self, text: str) -> np.ndarray:
        """Synthesize text to speech audio."""
        if not self._voice:
            return np.array([])

        try:
            # Piper synthesizes directly to audio chunks
            audio_chunks = []
            for chunk in self._voice.synthesize_stream_raw(
                text,
                length_scale=self.config.tts_length_scale,
                noise_scale=self.config.tts_noise_scale,
                noise_w=self.config.tts_noise_w,
            ):
                audio_chunks.append(chunk)

            if audio_chunks:
                audio = np.concatenate(audio_chunks)
                # Convert int16 to float32
                return audio.astype(np.float32) / 32768.0
            return np.array([])
        except Exception:
            logger.exception("TTS synthesis failed")
            return np.array([])


class VoiceManager:
    """High-level voice interaction manager.

    Args:
        config:        Voice system configuration.
        audio_backend: Audio I/O backend. Defaults to SounddeviceBackend.
                       Pass a custom AudioBackend for testing or alternative hardware.
    """

    def __init__(
        self,
        config: VoiceConfig | None = None,
        audio_backend: AudioBackend | None = None,
    ) -> None:
        self.config = config or VoiceConfig()
        self._audio: AudioBackend = audio_backend or SounddeviceBackend()
        self.wake_detector = WakeWordDetector(self.config)
        self.stt = SpeechToText(self.config)
        self.tts = TextToSpeech(self.config)
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize all voice components."""
        results = await asyncio.gather(
            self.wake_detector.initialize(),
            self.stt.initialize(),
            self.tts.initialize(),
            return_exceptions=True,
        )

        self._initialized = True
        wake_ok, stt_ok, tts_ok = results
        logger.info(
            "Voice system initialized: wake=%s, stt=%s, tts=%s, audio=%s",
            wake_ok, stt_ok, tts_ok, self._audio.is_available(),
        )
        return any(r is True for r in results)

    def list_input_devices(self) -> list[AudioDevice]:
        """Return available microphone devices."""
        return self._audio.list_input_devices()

    def list_output_devices(self) -> list[AudioDevice]:
        """Return available speaker devices."""
        return self._audio.list_output_devices()

    async def listen_for_wake_word(self) -> bool:
        """Listen for wake word activation."""
        if not self._audio.is_available():
            logger.error(
                "Audio backend not available. "
                "Install sounddevice: pip install sounddevice"
            )
            return False

        await self.wake_detector.start()
        chunk_samples = int(self.config.sample_rate * self.config.chunk_duration_ms / 1000)

        try:
            stream = await self._audio.open_input_stream(
                sample_rate=self.config.sample_rate,
                channels=self.config.channels,
                blocksize=chunk_samples,
                device=self.config.input_device,
            )
            with stream:
                while True:
                    chunk, _ = await asyncio.to_thread(stream.read, chunk_samples)
                    if await self.wake_detector.detect(chunk.flatten()):
                        logger.info("Wake word detected!")
                        return True
        except Exception:
            logger.exception("Wake word listening failed")
            return False
        finally:
            await self.wake_detector.stop()

    async def listen_and_transcribe(self, duration_seconds: float = 5.0) -> str:
        """Record audio and transcribe."""
        if not self._audio.is_available():
            logger.error("Audio backend not available; cannot record")
            return ""

        recording = await self._audio.record(
            duration_seconds=duration_seconds,
            sample_rate=self.config.sample_rate,
            channels=self.config.channels,
            device=self.config.input_device,
        )
        if len(recording) == 0:
            return ""
        return await self.stt.transcribe(recording)

    async def speak(self, text: str) -> bool:
        """Synthesize and play speech."""
        if not self._audio.is_available():
            logger.error("Audio backend not available; cannot play speech")
            return False

        audio = await self.tts.synthesize(text)
        if len(audio) == 0:
            return False

        await self._audio.play(
            audio,
            sample_rate=self.config.sample_rate,
            device=self.config.output_device,
        )
        return True

    async def conversation_turn(self) -> str | None:
        """Execute one conversation turn: wake → listen → transcribe → respond."""
        # Wait for wake word
        if not await self.listen_for_wake_word():
            return None

        # Play acknowledgment
        await self.speak("Yes?")

        # Listen for command
        command = await self.listen_and_transcribe(10.0)
        if not command:
            await self.speak("I didn't catch that.")
            return None

        return command

    def get_status(self) -> dict[str, Any]:
        """Get voice system status.

        Note: The returned dict uses ``wake_word`` as the key (not ``wake``).
        This is the canonical key name used by both this method and the CLI.
        """
        audio_available = self._audio.is_available()
        input_devs = self._audio.list_input_devices() if audio_available else []
        output_devs = self._audio.list_output_devices() if audio_available else []

        wake_enabled = self._initialized and _OPENWAKEWORD_AVAILABLE and self.wake_detector._model is not None
        stt_enabled = self._initialized and _FASTER_WHISPER_AVAILABLE and self.stt._model is not None
        tts_enabled = self._initialized and _PIPER_AVAILABLE and self.tts._model is not None

        return {
            "initialized": self._initialized,
            "wake_word": {
                "available": _OPENWAKEWORD_AVAILABLE,
                "enabled": wake_enabled,
                "model": self.config.wake_word_model,
                "threshold": self.config.wake_word_threshold,
            },
            "stt": {
                "available": _FASTER_WHISPER_AVAILABLE,
                "enabled": stt_enabled,
                "model": self.config.stt_model,
                "device": self.config.stt_device,
                "engine": "faster-whisper",
            },
            "tts": {
                "available": _PIPER_AVAILABLE,
                "enabled": tts_enabled,
                "model": self.config.tts_model,
                "voice": self.config.tts_model,
                "engine": "piper",
            },
            "audio": {
                "available": audio_available,
                "backend": type(self._audio).__name__,
                "sample_rate": self.config.sample_rate,
                "input_devices": len(input_devs),
                "output_devices": len(output_devs),
            },
        }