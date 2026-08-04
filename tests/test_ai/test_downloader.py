"""Tests for ModelDownloader."""

from __future__ import annotations

import pytest

from atlas.ai.downloader import DownloadError, DownloadResult, ModelDownloader


@pytest.fixture
def downloader(tmp_path):
    return ModelDownloader(models_dir=tmp_path)


async def test_download_stub_creates_file(downloader, tmp_path):
    result = await downloader.download(
        model_id="test-model",
        source_url="https://example.com/test-model.gguf",
    )
    assert isinstance(result, DownloadResult)
    assert result.success is True
    assert result.model_id == "test-model"
    assert result.path.exists()
    assert result.path.name == "test-model.gguf"


async def test_download_invokes_progress_callback(downloader):
    progress_calls = []

    async def _on_progress(model_id, downloaded, total):
        progress_calls.append((model_id, downloaded, total))

    result = await downloader.download(
        model_id="progress-model",
        source_url="https://example.com/model.gguf",
        progress_callback=_on_progress,
    )
    assert result.success is True
    assert len(progress_calls) > 0
    assert progress_calls[-1][1] == progress_calls[-1][2]  # downloaded == total at end


async def test_download_skips_existing_file_when_overwrite_false(downloader, tmp_path):
    dest = tmp_path / "existing.gguf"
    dest.write_bytes(b"\x00" * 50)

    result = await downloader.download(
        model_id="existing",
        source_url="https://example.com/existing.gguf",
        overwrite=False,
    )
    assert result.success is True
    assert result.bytes_downloaded == 50


async def test_download_from_huggingface_wrapper(downloader):
    result = await downloader.download_from_huggingface(
        repo_id="TheBloke/Llama-2-7B-GGUF",
        filename="llama-2-7b.Q4_K_M.gguf",
    )
    assert result.success is True
    assert result.model_id == "llama-2-7b.Q4_K_M"
    assert result.path.name == "llama-2-7b.Q4_K_M.gguf"
