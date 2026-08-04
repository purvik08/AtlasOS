"""Mock network state for the Atlas OS touch kiosk prototype.

``MeshModel`` stands in for the Network module's peer-discovery + local
model port table (mDNS mesh). ``WifiModel`` stands in for its WiFi scan
results.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, QObject, Qt, Slot


class MeshModel(QAbstractListModel):
    """Unified table of models served locally and by peer Atlas nodes."""

    HostnameRole = Qt.ItemDataRole.UserRole + 1
    ModelNameRole = Qt.ItemDataRole.UserRole + 2
    AddressRole = Qt.ItemDataRole.UserRole + 3
    IsLocalRole = Qt.ItemDataRole.UserRole + 4
    StatusRole = Qt.ItemDataRole.UserRole + 5

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._entries: list[dict[str, Any]] = [
            {
                "hostname": "atlas-desk",
                "model": "qwen2.5:3b-instruct",
                "address": "127.0.0.1:9001",
                "is_local": True,
                "status": "serving",
            },
            {
                "hostname": "atlas-livingroom.local",
                "model": "llama3.2:1b-instruct",
                "address": "192.168.1.53:9001",
                "is_local": False,
                "status": "serving",
            },
            {
                "hostname": "atlas-workshop.local",
                "model": "phi3.5:3.8b-mini",
                "address": "192.168.1.61:9001",
                "is_local": False,
                "status": "unreachable",
            },
        ]

    def roleNames(self) -> dict[int, bytes]:
        return {
            self.HostnameRole: b"hostname",
            self.ModelNameRole: b"modelName",
            self.AddressRole: b"address",
            self.IsLocalRole: b"isLocal",
            self.StatusRole: b"status",
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
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
        }.get(role)

    @Slot(int, str)
    def setAddress(self, row: int, address: str) -> None:
        """Edit the bind address:port of a *local* entry only."""

        if not (0 <= row < len(self._entries)) or not self._entries[row]["is_local"]:
            return
        self._entries[row]["address"] = address
        idx = self.index(row, 0)
        self.dataChanged.emit(idx, idx, [self.AddressRole])


class WifiModel(QAbstractListModel):
    """Mock WiFi scan results for the Network screen."""

    SsidRole = Qt.ItemDataRole.UserRole + 1
    SignalRole = Qt.ItemDataRole.UserRole + 2
    SecuredRole = Qt.ItemDataRole.UserRole + 3
    ConnectedRole = Qt.ItemDataRole.UserRole + 4

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._networks: list[dict[str, Any]] = [
            {"ssid": "Workshop-5G", "signal": 92, "secured": True, "connected": True},
            {"ssid": "Workshop-2.4G", "signal": 78, "secured": True, "connected": False},
            {"ssid": "Neighbor-WiFi", "signal": 34, "secured": True, "connected": False},
            {"ssid": "Atlas-Setup-AP", "signal": 100, "secured": False, "connected": False},
        ]

    def roleNames(self) -> dict[int, bytes]:
        return {
            self.SsidRole: b"ssid",
            self.SignalRole: b"signal",
            self.SecuredRole: b"secured",
            self.ConnectedRole: b"connected",
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
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
        }.get(role)

    @Slot(int)
    def connectTo(self, row: int) -> None:
        if not (0 <= row < len(self._networks)):
            return
        for i, entry in enumerate(self._networks):
            entry["connected"] = i == row
        self.dataChanged.emit(
            self.index(0, 0), self.index(len(self._networks) - 1, 0), [self.ConnectedRole]
        )
