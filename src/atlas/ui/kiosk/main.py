"""Entry point for the Atlas OS touch kiosk.

Run windowed for development::

    python -m atlas.ui.kiosk.main

Run fullscreen, as it will on-device::

    ATLAS_KIOSK_FULLSCREEN=1 python -m atlas.ui.kiosk.main

Optionally wire a live AIManager by setting ATLAS_MODELS_DIR to the directory
containing your GGUF files::

    ATLAS_MODELS_DIR=/home/purvik/models python -m atlas.ui.kiosk.main

If ATLAS_MODELS_DIR is unset or no GGUF files are found, ChatModel and
LlmModel fall back to mock / empty-list mode so the UI always starts.

The original comment about "swap in this file only" is preserved: QML screens
only bind to context property names (appState, chatModel, etc.) and never know
whether the data behind them is real or mocked.
"""

from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)

_QML_DIR = Path(__file__).resolve().parent / "qml"

# Default models directory — can be overridden by ATLAS_MODELS_DIR env var.
_DEFAULT_MODELS_DIR = Path(__file__).resolve().parents[4] / "models"


def _theme_provider(_engine: object) -> ThemeSingleton:
    return ThemeSingleton()


def _try_build_ai_manager(models_dir: Path) -> tuple[object | None, str]:
    """Attempt to build a live AIManager from GGUF files in *models_dir*.

    Returns
    -------
    (manager, session_id)
        Both are non-None only when at least one GGUF file exists and
        llama-cpp-python is installed.  On any failure both are None / "".
    """
    gguf_files = list(models_dir.rglob("*.gguf")) if models_dir.exists() else []
    if not gguf_files:
        logger.info(
            "Kiosk: no GGUF files in '%s' — running ChatModel in mock mode.",
            models_dir,
        )
        return None, ""

    try:
        import asyncio
        from atlas.ai.manager import AIManager
        from atlas.config.settings import AtlasConfig

        config = AtlasConfig(models_dir=str(models_dir))
        manager = AIManager(config)

        async def _start_and_session() -> str:
            await manager.start()
            # Open a persistent session on the first discovered model.
            first_model = gguf_files[0].stem
            await manager.load_model(first_model)
            session = manager.new_session(role="local", model_id=first_model)
            return session.session_id

        session_id = asyncio.run(_start_and_session())
        logger.info(
            "Kiosk: AIManager started with model '%s' (session=%s).",
            gguf_files[0].stem,
            session_id,
        )
        return manager, session_id

    except Exception as exc:
        logger.warning(
            "Kiosk: could not start AIManager (%s) — running ChatModel in mock mode.",
            exc,
        )
        return None, ""


def create_engine(app: QGuiApplication) -> QQmlApplicationEngine:
    """Build the QML engine with Theme singleton and all context properties.

    Kept separate from :func:`main` so tests can build and inspect an engine
    without also calling ``app.exec()``.
    """
    qmlRegisterSingletonType(ThemeSingleton, "AtlasUI", 1, 0, "Theme", _theme_provider)

    engine = QQmlApplicationEngine()
    context = engine.rootContext()

    # Resolve models directory from env var or project-relative default.
    models_dir = Path(os.environ.get("ATLAS_MODELS_DIR", str(_DEFAULT_MODELS_DIR)))

    # Try to bring up real AI inference; fall back gracefully on any error.
    ai_manager, session_id = _try_build_ai_manager(models_dir)

    context.setContextProperty("appState", AppState(app))
    context.setContextProperty(
        "chatModel",
        ChatModel(app, ai_manager=ai_manager, session_id=session_id),
    )
    context.setContextProperty(
        "llmModel",
        LlmModel(app, models_dir=str(models_dir)),
    )
    context.setContextProperty("meshModel", MeshModel(app))
    context.setContextProperty("wifiModel", WifiModel(app))
    context.setContextProperty("memoryModel", MemoryModel(app))
    context.setContextProperty(
        "fullscreenMode",
        os.environ.get("ATLAS_KIOSK_FULLSCREEN") == "1",
    )

    return engine


def main() -> int:
    """Launch the kiosk. Returns the process exit code."""
    QQuickStyle.setStyle("Material")

    app = QGuiApplication(sys.argv)
    engine = create_engine(app)
    engine.load(QUrl.fromLocalFile(str(_QML_DIR / "Main.qml")))

    if not engine.rootObjects():
        return 1

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
