"""Render all seven Atlas OS kiosk screens offscreen and save PNGs.

Used to prove the QML renders correctly without a display, and to generate
screenshots for documentation and review before running on real hardware.

Usage:
    python scripts/capture_kiosk_screens.py [output_dir]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonType
from PySide6.QtQuickControls2 import QQuickStyle

from atlas.ui.kiosk.controllers.app_state import AppState
from atlas.ui.kiosk.controllers.theme import ThemeSingleton
from atlas.ui.kiosk.models.chat_model import ChatModel
from atlas.ui.kiosk.models.llm_model import LlmModel
from atlas.ui.kiosk.models.memory_model import MemoryModel
from atlas.ui.kiosk.models.network_model import MeshModel, WifiModel

W, H = 1280, 720
QML_DIR = ROOT / "src/atlas/ui/kiosk/qml"

SCREENS = [
    ("home", 0),
    ("chat", 1),
    ("models", 2),
    ("network", 3),
    ("voice", 4),
    ("memory", 5),
    ("system", 6),
]

# Inline QML driver: load Main.qml, set the nav index from Python, grab the frame.
_DRIVER_QML = """
import QtQuick
import QtQuick.Window
import AtlasUI 1.0

Window {{
    id: win
    width: {w}; height: {h}
    visible: true
    color: Theme.bgPrimary

    property int screenIndex: 0

    Loader {{
        id: main
        anchors.fill: parent
        source: "{main_url}"
    }}
}}
""".format(
    w=W, h=H, main_url=QUrl.fromLocalFile(str(QML_DIR / "Main.qml")).toString()
)


def main(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    QQuickStyle.setStyle("Material")
    app = QGuiApplication(sys.argv)

    def theme_provider(_e):
        return ThemeSingleton()

    qmlRegisterSingletonType(ThemeSingleton, "AtlasUI", 1, 0, "Theme", theme_provider)

    app_state = AppState(app)
    chat_model = ChatModel(app)
    llm_model = LlmModel(app)
    mesh_model = MeshModel(app)
    wifi_model = WifiModel(app)
    memory_model = MemoryModel(app)

    results: list[tuple[str, bool]] = []
    current_idx = [0]

    def capture_next() -> None:
        if current_idx[0] >= len(SCREENS):
            app.quit()
            return

        name, tab_index = SCREENS[current_idx[0]]
        current_idx[0] += 1

        # Set the navigation index by updating the QML context and re-rendering
        engine = QQmlApplicationEngine()
        ctx = engine.rootContext()
        ctx.setContextProperty("appState", app_state)
        ctx.setContextProperty("chatModel", chat_model)
        ctx.setContextProperty("llmModel", llm_model)
        ctx.setContextProperty("meshModel", mesh_model)
        ctx.setContextProperty("wifiModel", wifi_model)
        ctx.setContextProperty("memoryModel", memory_model)
        ctx.setContextProperty("fullscreenMode", False)
        ctx.setContextProperty("initialTab", tab_index)

        # Load the individual screen directly for a clean per-screen shot
        # Write a minimal wrapper QML that hosts the screen.
        # Import paths are set on the engine, not inlined in QML, so no
        # absolute path strings appear inside the QML source.
        import textwrap, tempfile
        screen_files = [
            "HomeScreen", "ChatScreen", "ModelsScreen", "NetworkScreen",
            "VoiceScreen", "MemoryScreen", "SystemScreen"
        ]
        wrapper = textwrap.dedent(f"""
            import QtQuick
            import AtlasUI 1.0

            Rectangle {{
                width: {W}; height: {H}
                color: Theme.bgPrimary

                {screen_files[tab_index]} {{
                    anchors.fill: parent
                }}
            }}
        """)
        tf = tempfile.NamedTemporaryFile(suffix=".qml", delete=False, mode="w",
                                         dir=str(QML_DIR / "screens"))
        tf.write(wrapper)
        tf.close()

        engine.addImportPath(str(QML_DIR))
        engine.addImportPath(str(QML_DIR / "components"))
        engine.addImportPath(str(QML_DIR / "screens"))
        engine.load(QUrl.fromLocalFile(tf.name))

        def grab_and_continue() -> None:
            roots = engine.rootObjects()
            if not roots:
                print(f"  [WARN] No root objects for {name}")
                results.append((name, False))
                engine.deleteLater()
                QTimer.singleShot(0, capture_next)
                return
            win = roots[0]
            img = win.grabWindow()
            out_path = out_dir / f"screen_{name}.png"
            ok = img.save(str(out_path))
            size_kb = out_path.stat().st_size // 1024 if ok else 0
            print(f"  {'✓' if ok else '✗'} {name:12s} → {out_path.name} ({size_kb} KB)")
            results.append((name, ok))
            engine.deleteLater()
            import os
            os.unlink(tf.name)
            QTimer.singleShot(80, capture_next)

        QTimer.singleShot(300, grab_and_continue)

    QTimer.singleShot(0, capture_next)
    app.exec()

    passed = sum(1 for _, ok in results if ok)
    print(f"\n{passed}/{len(results)} screens captured to {out_dir}/")
    if passed < len(results):
        sys.exit(1)


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/atlas_screens")
    main(out)
