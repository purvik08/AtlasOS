"""Network and WiFi models for Atlas OS Dashboard.

Provides real WiFi scanning, access point signals, and connection management
via NetworkService / NetworkManager backend.
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, QObject, Qt, Signal, Slot

logger = logging.getLogger(__name__)


class WifiModel(QAbstractListModel):
    """WiFi scan results and real connection management."""

    SsidRole = Qt.ItemDataRole.UserRole + 1
    SignalRole = Qt.ItemDataRole.UserRole + 2
    SecuredRole = Qt.ItemDataRole.UserRole + 3
    ConnectedRole = Qt.ItemDataRole.UserRole + 4
    FrequencyRole = Qt.ItemDataRole.UserRole + 5
    BssidRole = Qt.ItemDataRole.UserRole + 6

    scanCompleted = Signal(int)
    connectionChanged = Signal(str, bool)
    scanRequested = Signal(str)
    connectRequested = Signal(str, str, str)
    errorOccurred = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._networks: list[dict[str, Any]] = []

    def roleNames(self) -> dict[int, bytes]:
        return {
            self.SsidRole: b"ssid",
            self.SignalRole: b"signal",
            self.SecuredRole: b"secured",
            self.ConnectedRole: b"connected",
            self.FrequencyRole: b"frequency",
            self.BssidRole: b"bssid",
        }

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        if parent is None:
            parent = QModelIndex()
        return 0 if parent.isValid() else len(self._networks)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._networks)):
            return None
        entry = self._networks[index.row()]
        return {
            self.SsidRole: entry["ssid"],
            self.SignalRole: entry["signal"],
            self.SecuredRole: entry["secured"],
            self.ConnectedRole: entry["connected"],
            self.FrequencyRole: entry["frequency"],
            self.BssidRole: entry["bssid"],
        }.get(role)

    @Slot(list)
    def updateNetworks(self, networks: list[dict[str, Any]]) -> None:
        """Update scan results from NetworkService / API."""
        self.beginResetModel()
        self._networks = []
        for n in networks:
            sig = n.get("signal_strength", n.get("signal", 0))
            if "secured" in n:
                is_secured = bool(n["secured"])
            else:
                sec = str(n.get("security", "WPA2")).lower()
                is_secured = sec not in ("open", "none", "")

            freq = n.get("frequency_mhz", 0)
            freq_str = f"{round(freq / 1000, 1)} GHz" if freq > 0 else n.get("frequency", "2.4 GHz")
            self._networks.append({
                "ssid": n.get("ssid", "(hidden)"),
                "signal": sig,
                "secured": is_secured,
                "connected": n.get("in_use", n.get("connected", False)),
                "frequency": freq_str,
                "bssid": n.get("bssid", ""),
            })
        self.endResetModel()
        self.scanCompleted.emit(len(self._networks))

    @Slot(int, str)
    def connectToNetwork(self, row: int, password: str = "") -> None:
        """Connect to network at row index."""
        if not (0 <= row < len(self._networks)):
            return
        ssid = self._networks[row]["ssid"]
        self.connectRequested.emit(ssid, password, "")

    @Slot(str)
    def scan(self, iface: str = "") -> None:
        """Trigger Wi-Fi scan."""
        self.scanRequested.emit(iface)


class MeshModel(QAbstractListModel):
    """LAN node discovery and endpoints model."""

    HostnameRole = Qt.ItemDataRole.UserRole + 1
    ModelNameRole = Qt.ItemDataRole.UserRole + 2
    AddressRole = Qt.ItemDataRole.UserRole + 3
    IsLocalRole = Qt.ItemDataRole.UserRole + 4
    StatusRole = Qt.ItemDataRole.UserRole + 5
    ProviderRole = Qt.ItemDataRole.UserRole + 6

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        import socket
        self._entries: list[dict[str, Any]] = [
            {
                "hostname": socket.gethostname(),
                "model": "Atlas Node",
                "address": "127.0.0.1:8000",
                "is_local": True,
                "status": "online",
                "provider": "local",
            }
        ]

    def roleNames(self) -> dict[int, bytes]:
        return {
            self.HostnameRole: b"hostname",
            self.ModelNameRole: b"modelName",
            self.AddressRole: b"address",
            self.IsLocalRole: b"isLocal",
            self.StatusRole: b"status",
            self.ProviderRole: b"provider",
        }

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        if parent is None:
            parent = QModelIndex()
        return 0 if parent.isValid() else len(self._entries)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._entries)):
            return None
        entry = self._entries[index.row()]
        return {
            self.HostnameRole: entry["hostname"],
            self.ModelNameRole: entry["model"],
            self.AddressRole: entry["address"],
            self.IsLocalRole: entry["is_local"],
            self.StatusRole: entry["status"],
            self.ProviderRole: entry["provider"],
        }.get(role)

    @Slot(list)
    def updateMesh(self, entries: list[dict[str, Any]]) -> None:
        self.beginResetModel()
        self._entries = entries
        self.endResetModel()