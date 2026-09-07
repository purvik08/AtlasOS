"""Shared pytest fixtures for Atlas OS UI tests."""

from __future__ import annotations

import sys
import pytest
from PySide6.QtGui import QGuiApplication


@pytest.fixture(scope="session")
def qapp():
    """Session-scoped QGuiApplication required for both QtCore models and QtQuick/QML UI."""
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv[:1])
    return app
