"""Tests for ModelDownloader — uses httpx mocking to avoid real network calls."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from atlas.ai.downloader import DownloadResult, ModelDownloader


@pytest.fixture
def downloader(tmp_path):
    return ModelDownloader(models_dir=tmp_path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_response(content: bytes, status_code: int = 200):
    """Build a minimal fake httpx streaming response."""
    response = MagicMock()
    response.status_code = status_code
    response.headers = {"content-length": str(len(content))}

    async def _aiter_bytes(chunk_size=65536):
        yield content

    response.aiter_bytes = _aiter_bytes
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=False)
    return response


def _make_fake_client(response):
    """Build a fake httpx.AsyncClient context manager."""
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.stream = MagicMock(return_value=response)
    return client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_download_stub_creates_file(downloader, tmp_path):
    fake_content = b"GGUF\x00" * 100
    fake_response = _make_fake_response(fake_content)
    fake_client = _make_fake_client(fake_response)

    with patch("atlas.ai.downloader.httpx.AsyncClient", return_value=fake_client):
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

    fake_content = b"X" * 1024
    fake_response = _make_fake_response(fake_content)
    fake_client = _make_fake_client(fake_response)

    with patch("atlas.ai.downloader.httpx.AsyncClient", return_value=fake_client):
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
    fake_content = b"MODEL" * 200
    fake_response = _make_fake_response(fake_content)
    fake_client = _make_fake_client(fake_response)

    with patch("atlas.ai.downloader.httpx.AsyncClient", return_value=fake_client):
        result = await downloader.download_from_huggingface(
            repo_id="TheBloke/Llama-2-7B-GGUF",
            filename="llama-2-7b.Q4_K_M.gguf",
        )

    assert result.success is True
    assert result.model_id == "llama-2-7b.Q4_K_M"
    assert result.path.name == "llama-2-7b.Q4_K_M.gguf"


async def test_download_checksum_verification_passes(downloader, tmp_path):
    import hashlib

    fake_content = b"CHECKSUM_TEST" * 10
    expected_sha256 = hashlib.sha256(fake_content).hexdigest()

    fake_response = _make_fake_response(fake_content)
    fake_client = _make_fake_client(fake_response)

    with patch("atlas.ai.downloader.httpx.AsyncClient", return_value=fake_client):
        result = await downloader.download(
            model_id="checksum-model",
            source_url="https://example.com/checksum.gguf",
            expected_sha256=expected_sha256,
        )

    assert result.success is True
    assert result.checksum_verified is True


async def test_download_bad_checksum_raises(downloader, tmp_path):
    from atlas.ai.downloader import ChecksumError

    fake_content = b"WRONG_DATA" * 10

    fake_response = _make_fake_response(fake_content)
    fake_client = _make_fake_client(fake_response)

    with patch("atlas.ai.downloader.httpx.AsyncClient", return_value=fake_client):
        with pytest.raises(ChecksumError):
            await downloader.download(
                model_id="bad-checksum-model",
                source_url="https://example.com/model.gguf",
                expected_sha256="0" * 64,  # Wrong hash
            )
