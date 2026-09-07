"""Tests for TerminalModel in AtlasOS Dashboard."""

from __future__ import annotations

import pytest
from PySide6.QtGui import QGuiApplication

from atlas.ui.dashboard.models.terminal_model import TerminalModel


@pytest.fixture
def qapp():
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])
    return app


def test_terminal_model_init(qapp):
    model = TerminalModel()
    assert "Atlas OS Embedded Terminal" in model.output
    assert model.prompt == "atlas@os:~$ "
    assert model.isBusy is False


def test_terminal_model_clear(qapp):
    model = TerminalModel()
    assert len(model.output) > 0
    model.clear()
    assert model.output == ""


def test_terminal_model_help(qapp):
    import time
    model = TerminalModel()
    model.executeCommand("help")
    for _ in range(120):
        qapp.processEvents()
        if not model.isBusy and ("Commands:" in model.output or "Usage:" in model.output):
            break
        time.sleep(0.05)
    assert "Usage:" in model.output or "Commands:" in model.output


def test_terminal_model_history(qapp):
    model = TerminalModel()
    model.executeCommand("atlas status")
    model.executeCommand("atlas models list")

    # Navigate up (-1)
    cmd = model.getHistory(-1)
    assert cmd == "atlas models list"
    cmd2 = model.getHistory(-1)
    assert cmd2 == "atlas status"

    # Navigate down (+1)
    cmd3 = model.getHistory(1)
    assert cmd3 == "atlas models list"


def test_terminal_model_python_execution(qapp):
    import time
    model = TerminalModel()
    model.executeCommand("python -c \"print('atlas_python_test_ok')\"")
    for _ in range(120):
        qapp.processEvents()
        if not model.isBusy and "atlas_python_test_ok" in model.output:
            break
        time.sleep(0.05)
    assert "atlas_python_test_ok" in model.output


def test_terminal_model_atlas_command(qapp):
    import time
    model = TerminalModel()
    model.executeCommand("atlas --version")
    for _ in range(120):
        qapp.processEvents()
        if not model.isBusy and ("atlas" in model.output.lower() or "version" in model.output.lower()):
            break
        time.sleep(0.05)
    assert "atlas" in model.output.lower() or "version" in model.output.lower()

