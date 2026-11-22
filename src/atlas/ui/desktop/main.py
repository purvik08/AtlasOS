"""Atlas OS Desktop - Qt6/QML application entry point."""

from __future__ import annotations

import sys
import os

# Ensure we can import atlas modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

def main() -> int:
    """Launch the Atlas OS Desktop Qt application."""
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtQml import QQmlApplicationEngine
        from PySide6.QtCore import QUrl, QCoreApplication
    except ImportError as e:
        print(f"Error: PySide6 not installed. Install with: pip install PySide6")
        print(f"Import error: {e}")
        return 1

    from atlas.ui.desktop.services.ApiService import ApiService

    # Set application metadata
    QCoreApplication.setApplicationName("Atlas OS Desktop")
    QCoreApplication.setApplicationVersion("0.1.0")
    QCoreApplication.setOrganizationName("Atlas OS")

    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Cross-platform consistent style

    engine = QQmlApplicationEngine()

    # Create API service
    api_service = ApiService()

    # Expose to QML context
    context = engine.rootContext()
    context.setContextProperty("apiService", api_service)

    # Load main QML
    qml_path = os.path.join(os.path.dirname(__file__), "resources", "qml", "Main.qml")
    if not os.path.exists(qml_path):
        print(f"Error: Main.qml not found at {qml_path}")
        return 1

    engine.load(QUrl.fromLocalFile(qml_path))

    if not engine.rootObjects():
        print("Error: Failed to load QML")
        return -1

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())