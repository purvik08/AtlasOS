"""Tests for ModelRegistry — scan, register, get, state tracking."""

from __future__ import annotations

import pytest

from atlas.ai.model import ModelNotFoundError, ModelRegistry
from atlas.ai.providers.base import ModelInfo


def _make_info(model_id: str, provider: str = "llama_cpp", loaded: bool = False) -> ModelInfo:
    return ModelInfo(
        model_id=model_id,
        display_name=model_id.title(),
        provider_name=provider,
        loaded=loaded,
    )


@pytest.fixture
def registry():
    return ModelRegistry()


# ---------------------------------------------------------------------------
# Register / unregister
# ---------------------------------------------------------------------------


def test_register_and_get(registry):
    info = _make_info("qwen-7b")
    registry.register(info)
    assert registry.get("qwen-7b") is not None
    assert registry.get("qwen-7b").model_id == "qwen-7b"


def test_register_overwrite_true(registry):
    registry.register(_make_info("m1"))
    new = _make_info("m1", provider="gemini")
    registry.register(new, overwrite=True)
    assert registry.get("m1").provider_name == "gemini"


def test_register_overwrite_false_keeps_original(registry):
    registry.register(_make_info("m1", provider="llama_cpp"))
    registry.register(_make_info("m1", provider="gemini"), overwrite=False)
    assert registry.get("m1").provider_name == "llama_cpp"


def test_unregister_removes_model(registry):
    registry.register(_make_info("bye"))
    registry.unregister("bye")
    assert "bye" not in registry


def test_unregister_unknown_raises(registry):
    with pytest.raises(ModelNotFoundError):
        registry.unregister("ghost")


def test_get_unknown_raises(registry):
    with pytest.raises(ModelNotFoundError):
        registry.get("nope")


# ---------------------------------------------------------------------------
# List / contains / len
# ---------------------------------------------------------------------------


def test_list_all_sorted_alphabetically(registry):
    registry.register(_make_info("z-model"))
    registry.register(_make_info("a-model"))
    ids = [m.model_id for m in registry.list_all()]
    assert ids == sorted(ids)


def test_model_ids(registry):
    registry.register(_make_info("m1"))
    registry.register(_make_info("m2"))
    assert set(registry.model_ids()) == {"m1", "m2"}


def test_contains(registry):
    registry.register(_make_info("present"))
    assert "present" in registry
    assert "absent" not in registry


def test_len(registry):
    assert len(registry) == 0
    registry.register(_make_info("a"))
    assert len(registry) == 1


# ---------------------------------------------------------------------------
# Loaded state management
# ---------------------------------------------------------------------------


def test_mark_loaded(registry):
    registry.register(_make_info("m", loaded=False))
    registry.mark_loaded("m")
    assert registry.get("m").loaded is True


def test_mark_unloaded(registry):
    registry.register(_make_info("m", loaded=True))
    registry.mark_unloaded("m")
    assert registry.get("m").loaded is False


def test_list_loaded(registry):
    registry.register(_make_info("a", loaded=True))
    registry.register(_make_info("b", loaded=False))
    loaded = registry.list_loaded()
    assert len(loaded) == 1
    assert loaded[0].model_id == "a"


def test_mark_loaded_unknown_raises(registry):
    with pytest.raises(ModelNotFoundError):
        registry.mark_loaded("ghost")


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------


def test_scan_empty_dir(registry, tmp_path):
    result = registry.scan(tmp_path)
    assert result == []


def test_scan_nonexistent_dir(registry, tmp_path):
    result = registry.scan(tmp_path / "does-not-exist")
    assert result == []


def test_scan_discovers_gguf(registry, tmp_path):
    (tmp_path / "my-model.gguf").write_bytes(b"\x00" * 1024)
    result = registry.scan(tmp_path)
    assert any(m.model_id == "my-model" for m in result)
    assert "my-model" in registry


def test_scan_ignores_non_gguf(registry, tmp_path):
    (tmp_path / "readme.txt").write_text("hello")
    result = registry.scan(tmp_path)
    assert result == []


def test_scan_records_file_size(registry, tmp_path):
    f = tmp_path / "sized.gguf"
    f.write_bytes(b"\x00" * 4096)
    registry.scan(tmp_path)
    assert registry.get("sized").size_bytes == 4096
