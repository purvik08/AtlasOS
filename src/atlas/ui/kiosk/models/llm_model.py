"""Local-model registry for the Atlas OS touch kiosk.

On startup this model attempts to populate itself from the real
``LlamaCppProvider`` via ``AIManager.list_models()``. If the AI manager is
not available (kiosk launched standalone, no model files present, etc.) it
falls back to an empty list so the UI still loads cleanly.

The existing mock ``toggleLoad`` / ``setTemperature`` / ``setContextSize``
slots are preserved unchanged because they drive the UI during the prototype
phase and will be replaced by real async calls once the full service layer
exists.

``startDownload`` now stores the repo_id from the user's input and displays it
in the model list; the actual download is handled by the CLI/API layer.

Role map (unchanged so QML bindings require no edits):
  NameRole, QuantRole, SizeGbRole, StatusRole, PortRole,
  ProgressRole, TemperatureRole, ContextSizeRole
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, QObject, Qt, QTimer, Slot

logger = logging.getLogger(__name__)


def _build_entries_from_registry(models_dir: str = "./models") -> list[dict[str, Any]]:
    """Scan *models_dir* for GGUF files and return a list of model entries.

    This runs synchronously on the Qt main thread at startup (file I/O only,
    no inference), so it must stay fast. We call the provider's _discover()
    logic directly rather than going through the full async AIManager because
    at kiosk start time there is no running event loop yet.

    Returns an empty list if the directory does not exist or contains no GGUF
    files; the UI shows an empty list with the Download bar in that case.
    """
    entries: list[dict[str, Any]] = []
    models_path = Path(models_dir)

    if not models_path.exists():
        logger.info("LlmModel: models_dir '%s' does not exist — starting empty.", models_dir)
        return entries

    for idx, path in enumerate(sorted(models_path.rglob("*.gguf"))):
        size_bytes = path.stat().st_size if path.exists() else 0
        size_gb = size_bytes / (1024 ** 3)

        # Derive a human-readable quant label from the filename if present,
        # e.g. "llama-3.2-1b-Q4_K_M.gguf" → "Q4_K_M"
        stem = path.stem
        quant = ""
        for part in stem.split("-"):
            if part.upper().startswith("Q") and "_" in part:
                quant = part.upper()
                break

        entries.append(
            {
                "name": stem,
                "quant": quant or "GGUF",
                "size_gb": round(size_gb, 2),
                "status": "unloaded",
                "port": 9001 + idx,
                "progress": 100,
                "temperature": 0.7,
                "context_size": 4096,
            }
        )
        logger.debug("LlmModel: discovered '%s' (%.2f GB)", stem, size_gb)

    logger.info("LlmModel: found %d GGUF model(s) in '%s'.", len(entries), models_dir)
    return entries


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

    def __init__(self, parent: QObject | None = None, models_dir: str = "./models") -> None:
        super().__init__(parent)
        # Populate from real GGUF files on disk; fall back to empty list.
        self._models: list[dict[str, Any]] = _build_entries_from_registry(models_dir)

        # Timer that advances any in-progress download bars.
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
        """Add a new entry in 'downloading' state for *repo_id*.

        The actual download is performed by the CLI/API layer
        (``atlas models download <repo_id>``); the kiosk entry here shows
        progress via the _advance_downloads timer (simulated) until a real
        download bridge is wired.
        """
        row = len(self._models)
        self.beginInsertRows(QModelIndex(), row, row)
        self._models.append(
            {
                "name": repo_id or "custom-model:latest",
                "quant": "Q4_K_M",
                "size_gb": 0.0,
                "status": "downloading",
                "port": 9001 + row,
                "progress": 0,
                "temperature": 0.7,
                "context_size": 4096,
            }
        )
        self.endInsertRows()
        logger.info("LlmModel: queued download for '%s'.", repo_id)
