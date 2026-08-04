"""Entry point for the Atlas OS touch kiosk prototype.

This is a UI shell with mock data standing in for the Local LLM, Network,
Voice, and Memory modules, built to validate the screen designs, navigation,
and the idle "robot face" animation on the target hardware (Raspberry Pi
Touch Display 2, 1280x720) before those backend modules exist.

Run windowed for development::

    python -m atlas.ui.kiosk.main

Run fullscreen, as it will on-device::

    ATLAS_KIOSK_FULLSCREEN=1 python -m atlas.ui.kiosk.main

Every mock model/controller here is written to the same shape the real
Local API client will expose, so swapping mock data for live data later is
meant to be a change in this file only -- the QML screens should not need
to change.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonType
from PySide6.QtQuickControls2 import QQuickStyle

from atlas.ui.kiosk.controllers.app_state import AppState
from atlas.ui.kiosk.controllers.theme import ThemeSingleton
from atlas.ui.kiosk.models.chat_model import ChatModel
from atlas.ui.kiosk.models.llm_model import LlmModel
from atlas.ui.kiosk.models.memory_model import MemoryModel
from atlas.ui.kiosk.models.network_model import MeshModel, WifiModel

_QML_DIR = Path(__file__).resolve().parent / "qml"


def _theme_provider(_engine: object) -> ThemeSingleton:
    return ThemeSingleton()


def create_engine(app: QGuiApplication) -> QQmlApplicationEngine:
    """Build the QML engine with the Theme singleton and mock state wired in.

    Kept separate from :func:`main` so tests can build and inspect an engine
    without also calling ``app.exec()``.
    """

    qmlRegisterSingletonType(ThemeSingleton, "AtlasUI", 1, 0, "Theme", _theme_provider)

    engine = QQmlApplicationEngine()
    context = engine.rootContext()

    context.setContextProperty("appState", AppState(app))
    context.setContextProperty("chatModel", ChatModel(app))
    context.setContextProperty("llmModel", LlmModel(app))
    context.setContextProperty("meshModel", MeshModel(app))
    context.setContextProperty("wifiModel", WifiModel(app))
    context.setContextProperty("memoryModel", MemoryModel(app))
    context.setContextProperty("fullscreenMode", os.environ.get("ATLAS_KIOSK_FULLSCREEN") == "1")

    return engine


def main() -> int:
    """Launch the kiosk prototype. Returns the process exit code."""

    QQuickStyle.setStyle("Material")

    app = QGuiApplication(sys.argv)
    engine = create_engine(app)
    engine.load(QUrl.fromLocalFile(str(_QML_DIR / "Main.qml")))

    if not engine.rootObjects():
        return 1

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
