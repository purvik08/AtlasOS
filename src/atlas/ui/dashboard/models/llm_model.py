"""Local and remote model registry model for Atlas OS Dashboard.

Provides real model listing, memory footprints, loaded/unloaded states,
and download/delete/load/unload operations directly from AtlasOS AI model management.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, QObject, Qt, Signal, Slot


class LlmModel(QAbstractListModel):
    """Real AI models: loaded/unloaded state, quantization, and parameters."""

    NameRole = Qt.ItemDataRole.UserRole + 1
    QuantRole = Qt.ItemDataRole.UserRole + 2
    SizeGbRole = Qt.ItemDataRole.UserRole + 3
    StatusRole = Qt.ItemDataRole.UserRole + 4
    PortRole = Qt.ItemDataRole.UserRole + 5
    ProgressRole = Qt.ItemDataRole.UserRole + 6
    TemperatureRole = Qt.ItemDataRole.UserRole + 7
    ContextSizeRole = Qt.ItemDataRole.UserRole + 8
    ProviderRole = Qt.ItemDataRole.UserRole + 9
    LoadedRole = Qt.ItemDataRole.UserRole + 10

    # Signals
    modelLoadRequested = Signal(str)
    modelUnloadRequested = Signal(str)
    modelDownloadRequested = Signal(str, str, str, str, str, bool)
    modelDeleteRequested = Signal(str, bool)
    modelRescanRequested = Signal()
    errorOccurred = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._models: list[dict[str, Any]] = []

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
            self.ProviderRole: b"provider",
            self.LoadedRole: b"loaded",
        }

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        if parent is None:
            parent = QModelIndex()
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
            self.ProviderRole: entry["provider"],
            self.LoadedRole: entry["loaded"],
        }.get(role)

    @Slot(list)
    def updateModelList(self, models: list[dict[str, Any]]) -> None:
        """Update model list from real backend registry data."""
        self.beginResetModel()
        self._models = []
        for m in models:
            size_bytes = m.get("size_bytes", 0)
            size_gb = round(size_bytes / (1024**3), 2) if size_bytes > 0 else 0.0
            is_loaded = m.get("loaded", False)
            self._models.append({
                "name": m.get("model_id", m.get("name", "")),
                "quant": m.get("quantization", "GGUF"),
                "size_gb": size_gb,
                "status": "loaded" if is_loaded else "unloaded",
                "port": m.get("port", 8000),
                "progress": 100,
                "temperature": float(m.get("temperature", 0.7)),
                "context_size": int(m.get("context_size", 4096)),
                "provider": m.get("provider", m.get("provider_name", "llama_cpp")),
                "loaded": is_loaded,
            })
        self.endResetModel()

    @Slot(str)
    def loadModel(self, model_id: str) -> None:
        """Request loading a model."""
        for i, m in enumerate(self._models):
            if m["name"] == model_id:
                m["status"] = "loading"
                idx = self.index(i, 0)
                self.dataChanged.emit(idx, idx, [self.StatusRole])
                break
        self.modelLoadRequested.emit(model_id)

    @Slot(str)
    def unloadModel(self, model_id: str) -> None:
        """Request unloading a model."""
        for i, m in enumerate(self._models):
            if m["name"] == model_id:
                m["status"] = "unloading"
                idx = self.index(i, 0)
                self.dataChanged.emit(idx, idx, [self.StatusRole])
                break
        self.modelUnloadRequested.emit(model_id)

    @Slot(str, str, str, str, str, bool)
    def downloadModel(
        self,
        model_id: str,
        url: str = "",
        repo: str = "",
        filename: str = "",
        token: str = "",
        overwrite: bool = False,
    ) -> None:
        """Request downloading a model from HF repo or URL."""
        self.modelDownloadRequested.emit(model_id, url, repo, filename, token, overwrite)

    @Slot(str, bool)
    def deleteModel(self, model_id: str, delete_file: bool = False) -> None:
        """Request deleting a model."""
        self.modelDeleteRequested.emit(model_id, delete_file)

    @Slot()
    def rescanModels(self) -> None:
        """Request rescanning models directory."""
        self.modelRescanRequested.emit()

    @Slot(int, float)
    def setTemperature(self, row: int, value: float) -> None:
        if 0 <= row < len(self._models):
            self._models[row]["temperature"] = value
            idx = self.index(row, 0)
            self.dataChanged.emit(idx, idx, [self.TemperatureRole])

    @Slot(int, int)
    def setContextSize(self, row: int, value: int) -> None:
        if 0 <= row < len(self._models):
            self._models[row]["context_size"] = value
            idx = self.index(row, 0)
            self.dataChanged.emit(idx, idx, [self.ContextSizeRole])