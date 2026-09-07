"""Atlas OS Dashboard - Unified Qt6/QML Desktop & Kiosk UI entry point.

Combines full-featured system dashboard with touch-optimized kiosk mode.
All models and controllers are bound to real AtlasOS backend services.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonType
from PySide6.QtQuickControls2 import QQuickStyle

from atlas.ui.dashboard.controllers.app_state import AppState
from atlas.ui.dashboard.controllers.theme import ThemeSingleton
from atlas.ui.dashboard.models.chat_model import ChatModel
from atlas.ui.dashboard.models.llm_model import LlmModel
from atlas.ui.dashboard.models.memory_model import MemoryModel
from atlas.ui.dashboard.models.network_model import MeshModel, WifiModel
from atlas.ui.dashboard.models.terminal_model import TerminalModel
from atlas.ui.dashboard.services.api_service import ApiService

if TYPE_CHECKING:
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine

_QML_DIR = Path(__file__).resolve().parent / "resources" / "qml"

KIOSK_MODE = os.environ.get("ATLAS_DASHBOARD_KIOSK", "0") == "1"
FULLSCREEN_MODE = os.environ.get("ATLAS_DASHBOARD_FULLSCREEN", "0") == "1"


def _theme_provider(_engine: object) -> ThemeSingleton:
    return ThemeSingleton()


def create_engine(app: QGuiApplication) -> QQmlApplicationEngine:
    """Build the QML engine with all real models and controllers connected."""

    # Register the Theme singleton
    qmlRegisterSingletonType(ThemeSingleton, "AtlasUI", 1, 0, "Theme", _theme_provider)

    engine = QQmlApplicationEngine()
    context = engine.rootContext()

    # Instantiate controllers & models
    app_state = AppState(app)
    chat_model = ChatModel(app)
    llm_model = LlmModel(app)
    mesh_model = MeshModel(app)
    wifi_model = WifiModel(app)
    memory_model = MemoryModel(app)
    terminal_model = TerminalModel(app)

    api_service = ApiService(
        base_url=os.environ.get("ATLAS_API_URL", "http://localhost:8000"),
        api_key=os.environ.get("ATLAS_API_KEY"),
        parent=app,
    )

    # ------------------------------------------------------------------
    # Model Registry Synchronization & Operations
    # ------------------------------------------------------------------
    def _on_model_registry(reg: Any) -> None:
        if reg and hasattr(reg, "models"):
            llm_model.updateModelList(reg.models)

    api_service.model_registry_changed.connect(_on_model_registry)
    api_service.system_info_changed.connect(app_state.updateFromSystemInfo)
    llm_model.modelLoadRequested.connect(api_service.load_model)
    llm_model.modelUnloadRequested.connect(api_service.unload_model)
    llm_model.modelDownloadRequested.connect(api_service.download_model)
    llm_model.modelDeleteRequested.connect(api_service.delete_model)
    llm_model.modelRescanRequested.connect(api_service.rescan_models)

    # ------------------------------------------------------------------
    # Chat & Token Streaming
    # ------------------------------------------------------------------
    api_service.streaming_chunk.connect(chat_model.appendStreamingChunk)
    api_service.streaming_finished.connect(chat_model.finishStreaming)
    api_service.session_messages_fetched.connect(chat_model.setSessionMessages)

    def _on_chat_sent(session_id: str, model_id: str, text: str) -> None:
        target_model = model_id
        if not target_model or target_model == "default":
            for m in llm_model._models:
                if m.get("loaded"):
                    target_model = m.get("name", "")
                    break
        api_service.stream_chat_message(session_id, target_model, text)

    chat_model.messageSent.connect(_on_chat_sent)

    # ------------------------------------------------------------------
    # Wi-Fi & Network
    # ------------------------------------------------------------------
    wifi_model.scanRequested.connect(api_service.scan_wifi)
    wifi_model.connectRequested.connect(api_service.connect_wifi)
    api_service.wifi_scan_completed.connect(wifi_model.updateNetworks)

    # ------------------------------------------------------------------
    # Persistent Memory
    # ------------------------------------------------------------------
    memory_model.rememberRequested.connect(api_service.remember_memory)
    memory_model.deleteRequested.connect(api_service.delete_memory)
    memory_model.fetchRequested.connect(api_service.fetch_memories)
    api_service.memories_changed.connect(memory_model.updateMemories)

    # ------------------------------------------------------------------
    # Expose to QML context
    # ------------------------------------------------------------------
    context.setContextProperty("appState", app_state)
    context.setContextProperty("chatModel", chat_model)
    context.setContextProperty("llmModel", llm_model)
    context.setContextProperty("meshModel", mesh_model)
    context.setContextProperty("wifiModel", wifi_model)
    context.setContextProperty("memoryModel", memory_model)
    context.setContextProperty("terminalModel", terminal_model)
    context.setContextProperty("apiService", api_service)
    context.setContextProperty("kioskMode", KIOSK_MODE)
    context.setContextProperty("fullscreenMode", FULLSCREEN_MODE)

    # QML import paths
    engine.addImportPath(str(_QML_DIR))
    engine.addImportPath(str(_QML_DIR / "components"))
    engine.addImportPath(str(_QML_DIR / "screens"))
    engine.addImportPath(str(_QML_DIR / "panels"))

    engine._api_service = api_service
    return engine


def main() -> int:
    """Launch the Atlas OS Dashboard. Returns process exit code."""
    if KIOSK_MODE:
        QQuickStyle.setStyle("Material")
        app = QGuiApplication(sys.argv)
    else:
        QQuickStyle.setStyle("Basic")
        from PySide6.QtWidgets import QApplication
        app = QApplication(sys.argv)
        app.setStyle("Fusion")

    engine = create_engine(app)

    main_qml = _QML_DIR / "Main.qml"
    if not main_qml.exists():
        print(f"Error: Main.qml not found at {main_qml}", file=sys.stderr)
        return 1

    engine.load(QUrl.fromLocalFile(str(main_qml)))

    if not engine.rootObjects():
        for err in engine.errors():
            print(f"QML Error: {err.toString()}")
        return 1

    if KIOSK_MODE and FULLSCREEN_MODE:
        root = engine.rootObjects()[0]
        if hasattr(root, "visibility"):
            root.visibility = root.FullScreen

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
