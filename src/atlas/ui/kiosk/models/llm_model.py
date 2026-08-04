"""Mock local-model registry for the Atlas OS touch kiosk prototype.

Stands in for the real Model Manager once the Local LLM module exists. Same
shape of data (name, quantization, size, status, port, sampling params) so
the Models screen doesn't change when real data replaces this.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, QObject, Qt, QTimer, Slot


class LlmModel(QAbstractListModel):
    """Local GGUF models: loaded/unloaded state, port, and sampling params."""

    NameRole = Qt.ItemDataRole.UserRole + 1
    QuantRole = Qt.ItemDataRole.UserRole + 2
    SizeGbRole = Qt.ItemDataRole.UserRole + 3
    StatusRole = Qt.ItemDataRole.UserRole + 4
    PortRole = Qt.ItemDataRole.UserRole + 5
    ProgressRole = Qt.ItemDataRole.UserRole + 6
    TemperatureRole = Qt.ItemDataRole.UserRole + 7
    ContextSizeRole = Qt.ItemDataRole.UserRole + 8

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._models: list[dict[str, Any]] = [
            {
                "name": "qwen2.5:3b-instruct",
                "quant": "Q4_K_M",
                "size_gb": 2.1,
                "status": "loaded",
                "port": 9001,
                "progress": 100,
                "temperature": 0.7,
                "context_size": 8192,
            },
            {
                "name": "llama3.2:1b-instruct",
                "quant": "Q4_0",
                "size_gb": 0.9,
                "status": "unloaded",
                "port": 9002,
                "progress": 100,
                "temperature": 0.8,
                "context_size": 4096,
            },
            {
                "name": "phi3.5:3.8b-mini",
                "quant": "Q4_K_M",
                "size_gb": 2.4,
                "status": "downloading",
                "port": 9003,
                "progress": 37,
                "temperature": 0.7,
                "context_size": 4096,
            },
        ]
        self._download_timer = QTimer(self)
        self._download_timer.timeout.connect(self._advance_downloads)
        self._download_timer.start(600)

    def roleNames(self) -> dict[int, bytes]:
        return {
            self.NameRole: b"name",
            self.QuantRole: b"quant",
            self.SizeGbRole: b"sizeGb",
            self.StatusRole: b"status",
            self.PortRole: b"port",
            self.ProgressRole: b"progress",
            self.TemperatureRole: b"temperature",
            self.ContextSizeRole: b"contextSize",
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._models)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._models)):
            return None
        entry = self._models[index.row()]
        return {
            self.NameRole: entry["name"],
            self.QuantRole: entry["quant"],
            self.SizeGbRole: entry["size_gb"],
            self.StatusRole: entry["status"],
            self.PortRole: entry["port"],
            self.ProgressRole: entry["progress"],
            self.TemperatureRole: entry["temperature"],
            self.ContextSizeRole: entry["context_size"],
        }.get(role)

    def _advance_downloads(self) -> None:
        for row, entry in enumerate(self._models):
            if entry["status"] == "downloading" and entry["progress"] < 100:
                entry["progress"] = min(100, entry["progress"] + 3)
                if entry["progress"] >= 100:
                    entry["status"] = "unloaded"
                idx = self.index(row, 0)
                self.dataChanged.emit(idx, idx, [self.ProgressRole, self.StatusRole])

    @Slot(int)
    def toggleLoad(self, row: int) -> None:
        if not (0 <= row < len(self._models)):
            return
        entry = self._models[row]
        if entry["status"] == "loaded":
            entry["status"] = "unloaded"
        elif entry["status"] == "unloaded":
            entry["status"] = "loaded"
        else:
            return
        idx = self.index(row, 0)
        self.dataChanged.emit(idx, idx, [self.StatusRole])

    @Slot(int, float)
    def setTemperature(self, row: int, value: float) -> None:
        if not (0 <= row < len(self._models)):
            return
        self._models[row]["temperature"] = value
        idx = self.index(row, 0)
        self.dataChanged.emit(idx, idx, [self.TemperatureRole])

    @Slot(int, int)
    def setContextSize(self, row: int, value: int) -> None:
        if not (0 <= row < len(self._models)):
            return
        self._models[row]["context_size"] = value
        idx = self.index(row, 0)
        self.dataChanged.emit(idx, idx, [self.ContextSizeRole])

    @Slot(str)
    def startDownload(self, repo_id: str) -> None:
        row = len(self._models)
        self.beginInsertRows(QModelIndex(), row, row)
        self._models.append(
            {
                "name": repo_id or "custom-model:latest",
                "quant": "Q4_K_M",
                "size_gb": 0.0,
                "status": "downloading",
                "port": 9000 + row + 1,
                "progress": 0,
                "temperature": 0.7,
                "context_size": 4096,
            }
        )
        self.endInsertRows()
