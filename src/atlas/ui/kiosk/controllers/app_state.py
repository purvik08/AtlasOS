"""Mock application state for the Atlas OS touch kiosk prototype.

``AppState`` stands in for the real Local API client that will exist once the
Local LLM, Network, Voice, and Memory modules are built. It exposes the same
shape of data and the same slots the real client will need, so wiring in a
real ``ApiClient`` later is a drop-in swap rather than a UI rewrite -- QML
screens bind to ``appState.<property>`` and call ``appState.<slot>()``
without knowing whether the data behind it is mocked or real.
"""

from __future__ import annotations

import random

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

_MOODS = ("idle", "listening", "thinking", "speaking", "error")


class AppState(QObject):
    """Central mock state: system stats, mood, voice, and device identity."""

    moodChanged = Signal()
    voiceEnabledChanged = Signal()
    voiceModeChanged = Signal()
    micLevelChanged = Signal()
    cpuPercentChanged = Signal()
    ramPercentChanged = Signal()
    tempCelsiusChanged = Signal()
    uptimeSecondsChanged = Signal()
    brightnessChanged = Signal()
    hostnameChanged = Signal()
    ipAddressChanged = Signal()
    toastRequested = Signal(str)  # transient message for the UI to display

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._mood = "idle"
        self._voice_enabled = True
        self._voice_mode = "wake_word"
        self._mic_level = 0.0
        self._cpu_percent = 12.0
        self._ram_percent = 41.0
        self._temp_celsius = 47.5
        self._uptime_seconds = 0
        self._brightness = 80
        self._hostname = "atlas-desk.local"
        self._ip_address = "192.168.1.42"

        self._uptime_timer = QTimer(self)
        self._uptime_timer.timeout.connect(self._tick_uptime)
        self._uptime_timer.start(1000)

        self._stats_timer = QTimer(self)
        self._stats_timer.timeout.connect(self._tick_stats)
        self._stats_timer.start(2000)

        self._mic_timer = QTimer(self)
        self._mic_timer.timeout.connect(self._tick_mic_level)
        self._mic_timer.start(120)

    # -- mood -----------------------------------------------------------------

    def _get_mood(self) -> str:
        return self._mood

    def _set_mood(self, value: str) -> None:
        if value not in _MOODS or value == self._mood:
            return
        self._mood = value
        self.moodChanged.emit()

    mood = Property(str, _get_mood, _set_mood, notify=moodChanged)

    @Slot(str)
    def setMood(self, value: str) -> None:
        self._set_mood(value)

    # -- voice ------------------------------------------------------------------

    def _get_voice_enabled(self) -> bool:
        return self._voice_enabled

    def _set_voice_enabled(self, value: bool) -> None:
        if value == self._voice_enabled:
            return
        self._voice_enabled = value
        self.voiceEnabledChanged.emit()
        self.toastRequested.emit("Voice control " + ("enabled" if value else "disabled"))
        if not value:
            self._set_mood("idle")

    voiceEnabled = Property(bool, _get_voice_enabled, _set_voice_enabled, notify=voiceEnabledChanged)

    @Slot()
    def toggleVoice(self) -> None:
        self._set_voice_enabled(not self._voice_enabled)

    def _get_voice_mode(self) -> str:
        return self._voice_mode

    def _set_voice_mode(self, value: str) -> None:
        if value == self._voice_mode:
            return
        self._voice_mode = value
        self.voiceModeChanged.emit()

    voiceMode = Property(str, _get_voice_mode, _set_voice_mode, notify=voiceModeChanged)

    @Slot(str)
    def setVoiceMode(self, value: str) -> None:
        self._set_voice_mode(value)

    def _get_mic_level(self) -> float:
        return self._mic_level

    micLevel = Property(float, _get_mic_level, notify=micLevelChanged)

    def _tick_mic_level(self) -> None:
        if self._mood in ("listening", "speaking") and self._voice_enabled:
            target = random.uniform(0.15, 0.95)
        else:
            target = 0.0
        # Ease toward the target instead of snapping, for a smoother meter.
        self._mic_level += (target - self._mic_level) * 0.4
        self.micLevelChanged.emit()

    # -- system stats (mock; real values come from HealthMonitor later) --------

    def _get_cpu_percent(self) -> float:
        return self._cpu_percent

    cpuPercent = Property(float, _get_cpu_percent, notify=cpuPercentChanged)

    def _get_ram_percent(self) -> float:
        return self._ram_percent

    ramPercent = Property(float, _get_ram_percent, notify=ramPercentChanged)

    def _get_temp_celsius(self) -> float:
        return self._temp_celsius

    tempCelsius = Property(float, _get_temp_celsius, notify=tempCelsiusChanged)

    def _tick_stats(self) -> None:
        self._cpu_percent = max(3.0, min(97.0, self._cpu_percent + random.uniform(-6, 6)))
        self._ram_percent = max(20.0, min(92.0, self._ram_percent + random.uniform(-2, 2)))
        self._temp_celsius = max(38.0, min(78.0, self._temp_celsius + random.uniform(-0.8, 0.8)))
        self.cpuPercentChanged.emit()
        self.ramPercentChanged.emit()
        self.tempCelsiusChanged.emit()

    def _get_uptime_seconds(self) -> int:
        return self._uptime_seconds

    uptimeSeconds = Property(int, _get_uptime_seconds, notify=uptimeSecondsChanged)

    def _tick_uptime(self) -> None:
        self._uptime_seconds += 1
        self.uptimeSecondsChanged.emit()

    # -- device -----------------------------------------------------------------

    def _get_brightness(self) -> int:
        return self._brightness

    def _set_brightness(self, value: int) -> None:
        value = max(10, min(100, value))
        if value == self._brightness:
            return
        self._brightness = value
        self.brightnessChanged.emit()

    brightness = Property(int, _get_brightness, _set_brightness, notify=brightnessChanged)

    @Slot(int)
    def setBrightness(self, value: int) -> None:
        self._set_brightness(value)

    def _get_hostname(self) -> str:
        return self._hostname

    hostname = Property(str, _get_hostname, notify=hostnameChanged)

    def _get_ip_address(self) -> str:
        return self._ip_address

    ipAddress = Property(str, _get_ip_address, notify=ipAddressChanged)

    # -- power actions (mock: surfaces a toast; real impl lands with System) ----

    @Slot()
    def requestReboot(self) -> None:
        self.toastRequested.emit("Reboot requested (mock -- no-op in prototype)")

    @Slot()
    def requestShutdown(self) -> None:
        self.toastRequested.emit("Shutdown requested (mock -- no-op in prototype)")
