"""Unit tests for LlmModel."""

from __future__ import annotations

import sys
import pytest
from PySide6.QtGui import QGuiApplication

from atlas.ui.dashboard.models.llm_model import LlmModel


@pytest.fixture(scope="session")
def qapp():
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv[:1])
    return app


class TestLlmModel:
    """Test LlmModel registry synchronization and parameter slots."""

    def test_update_model_list(self, qapp):
        model = LlmModel()
        data = [
            {
                "model_id": "qwen2.5-3b-instruct",
                "quantization": "Q4_K_M",
                "size_bytes": 2 * 1024**3,
                "loaded": True,
                "temperature": 0.7,
                "context_size": 8192,
                "provider": "llama_cpp",
            },
            {
                "model_id": "tinyllama-1.1b",
                "quantization": "Q4_K_M",
                "size_bytes": 1024**3,
                "loaded": False,
                "temperature": 0.8,
                "context_size": 4096,
                "provider": "llama_cpp",
            },
        ]
        model.updateModelList(data)
        assert model.rowCount() == 2

        idx0 = model.index(0, 0)
        assert model.data(idx0, model.NameRole) == "qwen2.5-3b-instruct"
        assert model.data(idx0, model.LoadedRole) is True
        assert model.data(idx0, model.SizeGbRole) == 2.0
        assert model.data(idx0, model.StatusRole) == "loaded"

        idx1 = model.index(1, 0)
        assert model.data(idx1, model.NameRole) == "tinyllama-1.1b"
        assert model.data(idx1, model.LoadedRole) is False
        assert model.data(idx1, model.StatusRole) == "unloaded"

    def test_adjust_parameters(self, qapp):
        model = LlmModel()
        model.updateModelList([{"model_id": "m1", "loaded": True}])
        idx = model.index(0, 0)

        model.setTemperature(0, 0.45)
        assert model.data(idx, model.TemperatureRole) == 0.45

        model.setContextSize(0, 16384)
        assert model.data(idx, model.ContextSizeRole) == 16384
