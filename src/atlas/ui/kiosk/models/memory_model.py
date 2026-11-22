"""Mock persistent-memory model for the Atlas OS touch kiosk prototype.

Stands in for the real Memory module's store. Browse, search, and delete
for this prototype; the real module will add semantic search and
conversation-linked provenance.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, QObject, Qt, Slot


class MemoryModel(QAbstractListModel):
    """Browsable list of the assistant's persistent memory entries."""

    SummaryRole = Qt.ItemDataRole.UserRole + 1
    CategoryRole = Qt.ItemDataRole.UserRole + 2
    TimestampRole = Qt.ItemDataRole.UserRole + 3

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._all_entries: list[dict[str, Any]] = [
            {
                "summary": "Prefers concise answers with code examples.",
                "category": "preference",
                "timestamp": "Jul 28",
            },
            {
                "summary": "Working on an ESP32-S3 drone flight controller PCB.",
                "category": "fact",
                "timestamp": "Jul 30",
            },
            {
                "summary": "Asked about GGUF quantization tradeoffs on Pi 5.",
                "category": "conversation",
                "timestamp": "Aug 01",
            },
            {"summary": "Timezone: Asia/Kolkata.", "category": "fact", "timestamp": "Jul 20"},
        ]
        self._visible_entries = list(self._all_entries)

    def roleNames(self) -> dict[int, bytes]:
        return {
            self.SummaryRole: b"summary",
            self.CategoryRole: b"category",
            self.TimestampRole: b"timestamp",
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._visible_entries)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._visible_entries)):
            return None
        entry = self._visible_entries[index.row()]
        return {
            self.SummaryRole: entry["summary"],
            self.CategoryRole: entry["category"],
            self.TimestampRole: entry["timestamp"],
        }.get(role)

    @Slot(str)
    def search(self, query: str) -> None:
        self.beginResetModel()
        query = query.strip().lower()
        if query:
            self._visible_entries = [e for e in self._all_entries if query in e["summary"].lower()]
        else:
            self._visible_entries = list(self._all_entries)
        self.endResetModel()

    @Slot(int)
    def deleteEntry(self, row: int) -> None:
        if not (0 <= row < len(self._visible_entries)):
            return
        entry = self._visible_entries[row]
        self.beginRemoveRows(QModelIndex(), row, row)
        self._visible_entries.remove(entry)
        if entry in self._all_entries:
            self._all_entries.remove(entry)
        self.endRemoveRows()
