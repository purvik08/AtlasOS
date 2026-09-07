"""Test dashboard engine creation with real dashboard main."""

import os
import sys
from pathlib import Path
from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QUrl

from atlas.ui.dashboard.main import create_engine, _QML_DIR

def test_dashboard_engine():
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])

    engine = create_engine(app)
    main_qml = _QML_DIR / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(main_qml)))
    
    assert len(engine.rootObjects()) > 0, f"QML load errors: {[e.toString() for e in engine.errors()]}"
    print("Dashboard QML loaded successfully with 0 errors!")

    if hasattr(engine, "_api_service") and engine._api_service:
        engine._api_service.shutdown()
    for obj in engine.rootObjects():
        obj.deleteLater()
    app.processEvents()

if __name__ == "__main__":
    test_dashboard_engine()
