"""Unit tests for MemoryModel."""

from __future__ import annotations

import sys
import pytest
from PySide6.QtGui import QGuiApplication

from atlas.ui.dashboard.models.memory_model import MemoryModel


@pytest.fixture(scope="session")
def qapp():
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv[:1])
    return app


class TestMemoryModel:
    """Test MemoryModel addition, deletion, and search filtering."""

    def test_add_and_delete_entry(self, qapp):
        model = MemoryModel()
        initial_count = model.rowCount()

        model.addEntry("Raspberry Pi 5 has 8GB RAM", "hardware", "user")
        assert model.rowCount() == initial_count + 1

        idx = model.index(model.rowCount() - 1, 0)
        assert model.data(idx, model.SummaryRole) == "Raspberry Pi 5 has 8GB RAM"
        assert model.data(idx, model.CategoryRole) == "hardware"

        model.deleteEntry(model.rowCount() - 1)
        assert model.rowCount() == initial_count

    def test_search_filter(self, qapp):
        model = MemoryModel()
        model.addEntry("AtlasOS is written in Python and QML", "fact", "system")
        model.addEntry("Dark mode is preferred", "preference", "user")

        model.search("Python")
        assert model.rowCount() >= 1

        model.clearSearch()
        assert model.rowCount() >= 2
