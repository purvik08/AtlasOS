"""Unit tests for Network models (WifiModel and MeshModel)."""

from __future__ import annotations

import sys
import pytest
from PySide6.QtGui import QGuiApplication

from atlas.ui.dashboard.models.network_model import MeshModel, WifiModel


@pytest.fixture(scope="session")
def qapp():
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv[:1])
    return app


class TestWifiModel:
    """Test WifiModel data updates and roles."""

    def test_update_networks(self, qapp):
        model = WifiModel()
        nets = [
            {"ssid": "Atlas-Lab-5G", "signal": 95, "secured": True, "connected": True, "frequency": "5.0 GHz", "bssid": "aa:bb:cc:dd:ee:ff"},
            {"ssid": "Guest-WiFi", "signal": 60, "secured": False, "connected": False, "frequency": "2.4 GHz", "bssid": "11:22:33:44:55:66"},
        ]
        model.updateNetworks(nets)
        assert model.rowCount() == 2

        idx0 = model.index(0, 0)
        assert model.data(idx0, model.SsidRole) == "Atlas-Lab-5G"
        assert model.data(idx0, model.SignalRole) == 95
        assert model.data(idx0, model.ConnectedRole) is True
        assert model.data(idx0, model.SecuredRole) is True


class TestMeshModel:
    """Test MeshModel endpoints."""

    def test_initial_entry(self, qapp):
        model = MeshModel()
        assert model.rowCount() >= 1
        idx = model.index(0, 0)
        assert model.data(idx, model.IsLocalRole) is True
        assert model.data(idx, model.StatusRole) == "online"
