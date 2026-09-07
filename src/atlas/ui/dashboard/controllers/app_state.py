"""Application state controller for Atlas OS Dashboard.

Manages real hardware metrics (CPU, RAM, Disk, Temperature, Uptime),
network IP/hostname, mic level, voice settings, and system power actions.
"""

from __future__ import annotations

import logging
import platform
import socket
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

logger = logging.getLogger(__name__)


def _read_soc_temperature() -> float:
    """Read CPU / SoC temperature in Celsius.

    Checks Raspberry Pi / Linux sysfs thermal zones first, then psutil if available.
    """
    # 1. Linux sysfs (standard on Raspberry Pi / embedded Linux)
    thermal_paths = [
        Path("/sys/class/thermal/thermal_zone0/temp"),
        Path("/sys/devices/virtual/thermal/thermal_zone0/temp"),
    ]
    for p in thermal_paths:
        try:
            if p.exists():
                content = p.read_text(encoding="utf-8").strip()
                val = float(content)
                # Value is usually in millidegrees C (e.g. 48500 = 48.5°C)
                return round(val / 1000.0, 1) if val > 1000 else round(val, 1)
        except Exception:
            pass

    # 2. psutil sensors_temperatures (Linux/macOS)
    try:
        import psutil
        if hasattr(psutil, "sensors_temperatures"):
            temps = psutil.sensors_temperatures()
            if temps:
                for _name, entries in temps.items():
                    if entries:
                        return round(entries[0].current, 1)
    except Exception:
        pass

    # 3. Fallback: simulate plausible room temperature baseline on non-supported hardware
    return 42.0


class AppState(QObject):
    """Global application state exposed to QML with reactive signals."""

    # Notification Signals
    moodChanged = Signal(str)
    ipAddressChanged = Signal(str)
    hostnameChanged = Signal(str)
    metricsChanged = Signal()
    voiceStateChanged = Signal()
    brightnessChanged = Signal(int)
    toastRequested = Signal(str, str)  # message, type: info/success/warning/error
    systemInfoChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._mood = "idle"
        self._ip_address = self._get_local_ip()
        self._hostname = socket.gethostname()
        self._cpu_percent = 0.0
        self._ram_percent = 0.0
        self._ram_used_gb = 0.0
        self._ram_total_gb = 0.0
        self._disk_percent = 0.0
        self._disk_used_gb = 0.0
        self._disk_total_gb = 0.0
        self._temp_celsius = 42.0
        self._boot_time_ts = 0.0
        self._uptime_seconds = 0
        self._mic_level = 0.0
        self._voice_enabled = True
        self._voice_mode = "wake_word"  # wake_word or push_to_talk
        self._brightness = 80
        self._system_info: dict[str, Any] = {}

        # Metric update timer (runs every 2 seconds)
        self._update_timer = QTimer(self)
        self._update_timer.setInterval(2000)
        self._update_timer.timeout.connect(self._update_system_metrics)
        self._update_timer.start()

        # Initial metric collection
        self._update_system_metrics()

    def _get_local_ip(self) -> str:
        """Get local network IP address."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"

    def _update_system_metrics(self) -> None:
        """Query real OS and hardware metrics."""
        try:
            import psutil

            # CPU & Memory
            self._cpu_percent = round(psutil.cpu_percent(interval=None), 1)
            vmem = psutil.virtual_memory()
            self._ram_percent = round(vmem.percent, 1)
            self._ram_used_gb = round(vmem.used / (1024**3), 2)
            self._ram_total_gb = round(vmem.total / (1024**3), 2)

            # Disk
            root_path = "C:\\" if platform.system() == "Windows" else "/"
            disk = psutil.disk_usage(root_path)
            self._disk_percent = round(disk.percent, 1)
            self._disk_used_gb = round(disk.used / (1024**3), 1)
            self._disk_total_gb = round(disk.total / (1024**3), 1)

            # Uptime & Boot time
            self._boot_time_ts = psutil.boot_time()
            self._uptime_seconds = int(datetime.now().timestamp() - self._boot_time_ts)

            # Temperature
            self._temp_celsius = _read_soc_temperature()

            # Consolidated dictionary
            self._system_info = {
                "cpu_percent": self._cpu_percent,
                "memory_percent": self._ram_percent,
                "memory_used_gb": self._ram_used_gb,
                "memory_total_gb": self._ram_total_gb,
                "disk_percent": self._disk_percent,
                "disk_used_gb": self._disk_used_gb,
                "disk_total_gb": self._disk_total_gb,
                "temperature_c": self._temp_celsius,
                "uptime_seconds": self._uptime_seconds,
                "boot_time": datetime.fromtimestamp(self._boot_time_ts).strftime("%Y-%m-%d %H:%M"),
                "ip_address": self._ip_address,
                "hostname": self._hostname,
                "os": platform.system(),
                "arch": platform.machine(),
                "python": platform.python_version(),
            }

            self.metricsChanged.emit()
            self.systemInfoChanged.emit()

        except Exception as exc:
            logger.warning("Error collecting system metrics: %s", exc)

    # -----------------------------------------------------------------------
    # Properties for QML
    # -----------------------------------------------------------------------

    @Property(str, notify=moodChanged)
    def mood(self) -> str:
        return self._mood

    @mood.setter
    def mood(self, val: str) -> None:
        if self._mood != val:
            self._mood = val
            self.moodChanged.emit(val)

    @Property(str, notify=ipAddressChanged)
    def ipAddress(self) -> str:
        return self._ip_address

    @Property(str, notify=hostnameChanged)
    def hostname(self) -> str:
        return self._hostname

    @Property(float, notify=metricsChanged)
    def cpuPercent(self) -> float:
        return self._cpu_percent

    @Property(float, notify=metricsChanged)
    def ramPercent(self) -> float:
        return self._ram_percent

    @Property(float, notify=metricsChanged)
    def ramUsedGb(self) -> float:
        return self._ram_used_gb

    @Property(float, notify=metricsChanged)
    def ramTotalGb(self) -> float:
        return self._ram_total_gb

    @Property(float, notify=metricsChanged)
    def diskPercent(self) -> float:
        return self._disk_percent

    @Property(float, notify=metricsChanged)
    def diskUsedGb(self) -> float:
        return self._disk_used_gb

    @Property(float, notify=metricsChanged)
    def diskTotalGb(self) -> float:
        return self._disk_total_gb

    @Property(float, notify=metricsChanged)
    def tempCelsius(self) -> float:
        return self._temp_celsius

    @Property(int, notify=metricsChanged)
    def uptimeSeconds(self) -> int:
        return self._uptime_seconds

    @Property(float, notify=voiceStateChanged)
    def micLevel(self) -> float:
        return self._mic_level

    @Property(bool, notify=voiceStateChanged)
    def voiceEnabled(self) -> bool:
        return self._voice_enabled

    @Property(str, notify=voiceStateChanged)
    def voiceMode(self) -> str:
        return self._voice_mode

    @Property(int, notify=brightnessChanged)
    def brightness(self) -> int:
        return self._brightness

    @Property("QVariant", notify=systemInfoChanged)
    def systemInfo(self) -> dict[str, Any]:
        return self._system_info

    @Property(str, constant=True)
    def platform(self) -> str:
        return platform.system()

    @Property(str, constant=True)
    def platformVersion(self) -> str:
        return platform.release()

    @Property(str, constant=True)
    def pythonVersion(self) -> str:
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    # -----------------------------------------------------------------------
    # Slots
    # -----------------------------------------------------------------------

    @Slot(str)
    def setMood(self, mood: str) -> None:
        self.mood = mood

    @Slot(float)
    def setMicLevel(self, level: float) -> None:
        self._mic_level = max(0.0, min(1.0, level))
        self.voiceStateChanged.emit()

    @Slot()
    def toggleVoice(self) -> None:
        self._voice_enabled = not self._voice_enabled
        self.voiceStateChanged.emit()

    @Slot(str)
    def setVoiceMode(self, mode: str) -> None:
        if mode in ("wake_word", "push_to_talk"):
            self._voice_mode = mode
            self.voiceStateChanged.emit()

    @Slot(int)
    def setBrightness(self, val: int) -> None:
        self._brightness = max(10, min(100, val))
        self.brightnessChanged.emit(self._brightness)

    @Slot(str, str)
    def showToast(self, message: str, toast_type: str = "info") -> None:
        """Request a toast notification in the UI."""
        self.toastRequested.emit(message, toast_type)

    @Slot()
    def refreshSystemInfo(self) -> None:
        """Manually trigger system info refresh."""
        self._ip_address = self._get_local_ip()
        self.ipAddressChanged.emit(self._ip_address)
        self._update_system_metrics()

    @Slot("QVariant")
    def updateFromSystemInfo(self, info: Any) -> None:
        """Sync local dashboard state from backend system info."""
        if not isinstance(info, dict):
            if hasattr(info, "model_dump"):
                info = info.model_dump()
            else:
                return

        self._cpu_percent = round(float(info.get("cpu_percent", self._cpu_percent)), 1)
        self._ram_percent = round(float(info.get("memory_percent", self._ram_percent)), 1)
        self._ram_used_gb = round(float(info.get("memory_used_gb", self._ram_used_gb)), 2)
        self._ram_total_gb = round(float(info.get("memory_total_gb", self._ram_total_gb)), 2)
        self._disk_percent = round(float(info.get("disk_percent", self._disk_percent)), 1)
        self._disk_used_gb = round(float(info.get("disk_used_gb", self._disk_used_gb)), 1)
        self._disk_total_gb = round(float(info.get("disk_total_gb", self._disk_total_gb)), 1)
        self._uptime_seconds = int(float(info.get("uptime_seconds", self._uptime_seconds)))
        if info.get("temperature_c") is not None:
            self._temp_celsius = round(float(info["temperature_c"]), 1)

        hostname = str(info.get("hostname", self._hostname))
        ip_address = str(info.get("ip_address", self._ip_address))
        if hostname != self._hostname:
            self._hostname = hostname
            self.hostnameChanged.emit(self._hostname)
        if ip_address != self._ip_address:
            self._ip_address = ip_address
            self.ipAddressChanged.emit(self._ip_address)

        self._system_info = dict(info)
        self.metricsChanged.emit()
        self.systemInfoChanged.emit()

    @Slot()
    def requestReboot(self) -> None:
        """Trigger system reboot."""
        logger.warning("Reboot requested from UI")
        self.showToast("System rebooting...", "warning")
        try:
            import subprocess
            if platform.system() == "Windows":
                subprocess.Popen(["shutdown", "/r", "/t", "1"])
            else:
                subprocess.Popen(["sudo", "reboot"])
        except Exception as exc:
            logger.error("Failed to execute reboot: %s", exc)
            self.showToast(f"Reboot failed: {exc}", "error")

    @Slot()
    def requestShutdown(self) -> None:
        """Trigger system shutdown."""
        logger.warning("Shutdown requested from UI")
        self.showToast("System shutting down...", "warning")
        try:
            import subprocess
            if platform.system() == "Windows":
                subprocess.Popen(["shutdown", "/s", "/t", "1"])
            else:
                subprocess.Popen(["sudo", "poweroff"])
        except Exception as exc:
            logger.error("Failed to execute shutdown: %s", exc)
            self.showToast(f"Shutdown failed: {exc}", "error")
