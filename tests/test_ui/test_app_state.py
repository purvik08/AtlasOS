"""Unit tests for AppState controller and telemetry."""

from __future__ import annotations

import sys
import pytest
from PySide6.QtGui import QGuiApplication

from atlas.ui.dashboard.controllers.app_state import AppState, _read_soc_temperature


@pytest.fixture(scope="session")
def qapp():
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv[:1])
    return app


class TestAppState:
    """Test AppState telemetry, properties, and signals."""

    def test_instantiation(self, qapp):
        state = AppState()
        assert state is not None
        assert state.mood == "idle"
        assert len(state.ipAddress) > 0
        assert len(state.hostname) > 0

    def test_metrics_collection(self, qapp):
        state = AppState()
        state.refreshSystemInfo()

        assert 0.0 <= state.cpuPercent <= 100.0
        assert 0.0 <= state.ramPercent <= 100.0
        assert state.ramTotalGb > 0.0
        assert state.diskTotalGb > 0.0
        assert state.tempCelsius > 0.0
        assert state.uptimeSeconds >= 0

        info = state.systemInfo
        assert "cpu_percent" in info
        assert "memory_percent" in info
        assert "disk_percent" in info
        assert "temperature_c" in info

    def test_voice_properties(self, qapp):
        state = AppState()
        assert state.voiceEnabled is True
        state.toggleVoice()
        assert state.voiceEnabled is False

        state.setVoiceMode("push_to_talk")
        assert state.voiceMode == "push_to_talk"

        state.setMicLevel(0.75)
        assert abs(state.micLevel - 0.75) < 1e-4

    def test_brightness_adjustment(self, qapp):
        state = AppState()
        state.setBrightness(90)
        assert state.brightness == 90
        # Clamped bounds
        state.setBrightness(150)
        assert state.brightness == 100
        state.setBrightness(2)
        assert state.brightness == 10

    def test_read_soc_temperature(self):
        temp = _read_soc_temperature()
        assert isinstance(temp, float)
        assert 10.0 <= temp <= 110.0
