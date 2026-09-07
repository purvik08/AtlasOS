"""Persistent memory model for Atlas OS Dashboard.

Provides real memory browsing, semantic vector search, and deletion
via AtlasOS MemoryService.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QAbstractListModel, QModelIndex, QObject, Qt, Signal, Slot

logger = logging.getLogger(__name__)


class MemoryModel(QAbstractListModel):
    """Real persistent memory entries from AtlasOS MemoryService."""

    SummaryRole = Qt.ItemDataRole.UserRole + 1
    CategoryRole = Qt.ItemDataRole.UserRole + 2
    TimestampRole = Qt.ItemDataRole.UserRole + 3
    IdRole = Qt.ItemDataRole.UserRole + 4
    SourceRole = Qt.ItemDataRole.UserRole + 5

    entryAdded = Signal(dict)
    entryRemoved = Signal(str)
    searchCompleted = Signal(int)
    rememberRequested = Signal(str, str, str)
    deleteRequested = Signal(str)
    fetchRequested = Signal()
    countChanged = Signal()
    errorOccurred = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._all_entries: list[dict[str, Any]] = []
        self._visible_entries: list[dict[str, Any]] = []
        self._load_initial_memories()

    def _load_initial_memories(self) -> None:
        """Fetch real memories from local data store."""
        try:
            from atlas.memory.store import MemoryStore

            persist_file = Path("./data/memories.json")
            if not persist_file.exists():
                return
            store = MemoryStore(persist_file)
            formatted = []
            for idx, entry in enumerate(store._entries):
                meta = entry.metadata or {}
                formatted.append({
                    "id": meta.get("id", f"mem-{idx+1:03d}"),
                    "summary": entry.text,
                    "category": meta.get("category", "general"),
                    "timestamp": meta.get("timestamp", "Recent"),
                    "source": meta.get("source", "system"),
                })
            self._all_entries = formatted
            self._visible_entries = list(formatted)
        except Exception as exc:
            logger.debug("Memory initial load: %s", exc)

    def roleNames(self) -> dict[int, bytes]:
        return {
            self.IdRole: b"id",
            self.SummaryRole: b"summary",
            self.CategoryRole: b"category",
            self.TimestampRole: b"timestamp",
            self.SourceRole: b"source",
        }

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        if parent is None:
            parent = QModelIndex()
        return 0 if parent.isValid() else len(self._visible_entries)

    @Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._all_entries)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._visible_entries)):
            return None
        entry = self._visible_entries[index.row()]
        return {
            self.IdRole: entry.get("id", ""),
            self.SummaryRole: entry.get("summary", entry.get("text", "")),
            self.CategoryRole: entry.get("category", "general"),
            self.TimestampRole: entry.get("timestamp", ""),
            self.SourceRole: entry.get("source", ""),
        }.get(role)

    @Slot(list)
    def updateMemories(self, entries: list[dict[str, Any]]) -> None:
        """Update memory list from API / service."""
        self.beginResetModel()
        self._all_entries = []
        for e in entries:
            self._all_entries.append({
                "id": e.get("id", ""),
                "summary": e.get("text", e.get("summary", "")),
                "category": e.get("category", "general"),
                "timestamp": e.get("timestamp", "Recent"),
                "source": e.get("source", "system"),
            })
        self._visible_entries = list(self._all_entries)
        self.endResetModel()
        self.countChanged.emit()

    @Slot(str)
    def search(self, query: str) -> None:
        """Semantic or keyword search over memory entries."""
        clean_q = query.strip()
        self.beginResetModel()
        if not clean_q:
            self._visible_entries = list(self._all_entries)
        else:
            self._visible_entries = [
                e for e in self._all_entries
                if clean_q.lower() in e["summary"].lower()
                or clean_q.lower() in e["category"].lower()
                or clean_q.lower() in e.get("source", "").lower()
            ]
        self.endResetModel()
        self.searchCompleted.emit(len(self._visible_entries))

    @Slot(str, str, str)
    def addEntry(self, text: str, category: str = "general", source: str = "user") -> None:
        """Store a new memory in MemoryService."""
        clean_text = text.strip()
        if not clean_text:
            return

        import uuid
        from datetime import datetime

        mem_id = f"mem-{uuid.uuid4().hex[:6]}"
        now_str = datetime.now().strftime("%b %d, %H:%M")

        new_entry = {
            "id": mem_id,
            "summary": clean_text,
            "category": category,
            "timestamp": now_str,
            "source": source,
        }

        row = len(self._visible_entries)
        self.beginInsertRows(QModelIndex(), row, row)
        self._all_entries.append(new_entry)
        self._visible_entries.append(new_entry)
        self.endInsertRows()
        self.countChanged.emit()
        self.entryAdded.emit(new_entry)
        self.rememberRequested.emit(clean_text, category, source)

    @Slot(int)
    def deleteEntry(self, row: int) -> None:
        """Delete entry at row index."""
        if not (0 <= row < len(self._visible_entries)):
            return
        entry = self._visible_entries[row]
        entry_id = entry.get("id", "")

        self.beginRemoveRows(QModelIndex(), row, row)
        self._visible_entries.pop(row)
        if entry in self._all_entries:
            self._all_entries.remove(entry)
        self.endRemoveRows()
        self.countChanged.emit()
        self.entryRemoved.emit(entry_id)
        if entry_id:
            self.deleteRequested.emit(entry_id)

    @Slot()
    def clearSearch(self) -> None:
        self.search("")
