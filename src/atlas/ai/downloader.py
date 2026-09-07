"""Production-grade model file downloader for Atlas OS.

Features
--------
* Async streaming download via ``httpx.AsyncClient``.
* Resume capability using HTTP ``Range`` headers for partial downloads.
* Progress reporting callbacks ``(model_id, bytes_downloaded, total_bytes)``.
* Optional SHA-256 checksum verification.
* Automatic model registration into :class:`~atlas.ai.model.ModelRegistry`.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import anyio
import httpx

if TYPE_CHECKING:
    from atlas.ai.model import ModelRegistry

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str, int, int], Awaitable[None]]


@dataclass
class DownloadResult:
    """Result of a download attempt."""

    model_id: str
    success: bool
    path: Path = field(default_factory=Path)
    error: str = ""
    bytes_downloaded: int = 0
    checksum_verified: bool = False


class DownloadError(RuntimeError):
    """Raised when a download fails."""


class ChecksumError(DownloadError):
    """Raised when SHA-256 checksum verification fails."""


class ModelDownloader:
    """Downloads model files with resume, progress callbacks, and SHA-256 verification.

    Parameters
    ----------
    models_dir:
        Destination directory for downloaded files.
    registry:
        Optional :class:`~atlas.ai.model.ModelRegistry` for automatic registration.
    """

    def __init__(
        self,
        models_dir: str | Path = "./models",
        registry: ModelRegistry | None = None,
    ) -> None:
        self._models_dir = Path(models_dir)
        self._registry = registry
        logger.debug("ModelDownloader initialised; target=%s", self._models_dir)

    def verify_checksum(self, file_path: Path, expected_sha256: str) -> bool:
        """Verify the SHA-256 hash of a local file."""
        if not file_path.exists():
            return False
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        calculated = hasher.hexdigest().lower()
        return calculated == expected_sha256.lower()

    async def download(
        self,
        model_id: str,
        source_url: str,
        *,
        filename: str | None = None,
        expected_sha256: str | None = None,
        progress_callback: ProgressCallback | None = None,
        overwrite: bool = False,
    ) -> DownloadResult:
        """Download a file with HTTP Range resume and SHA-256 check.

        Parameters
        ----------
        model_id:
            Identifier assigned to this model.
        source_url:
            URL to download from.
        filename:
            Override local filename. Defaults to derived name from URL or model_id.
        expected_sha256:
            Optional SHA-256 hex string to verify file integrity.
        progress_callback:
            Async callback ``(model_id, downloaded_bytes, total_bytes)``.
        overwrite:
            Re-download from scratch even if file exists.
        """
        dest_filename = filename or self._filename_from_url(source_url, model_id)
        dest_path = self._models_dir / dest_filename
        part_path = self._models_dir / f"{dest_filename}.part"

        self._models_dir.mkdir(parents=True, exist_ok=True)

        if dest_path.exists() and not overwrite:
            if expected_sha256:
                if not self.verify_checksum(dest_path, expected_sha256):
                    logger.warning("Existing file failed checksum; re-downloading.")
                else:
                    self._auto_register(model_id, dest_path)
                    return DownloadResult(
                        model_id=model_id,
                        success=True,
                        path=dest_path,
                        bytes_downloaded=dest_path.stat().st_size,
                        checksum_verified=True,
                    )
            else:
                self._auto_register(model_id, dest_path)
                return DownloadResult(
                    model_id=model_id,
                    success=True,
                    path=dest_path,
                    bytes_downloaded=dest_path.stat().st_size,
                    checksum_verified=False,
                )

        # Check existing partial download for resume
        downloaded = part_path.stat().st_size if part_path.exists() and not overwrite else 0
        headers = {}
        if downloaded > 0:
            headers["Range"] = f"bytes={downloaded}-"
            logger.info("Resuming download for '%s' from byte %d.", model_id, downloaded)
        else:
            mode = "wb"

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=300.0) as client:
                async with client.stream("GET", source_url, headers=headers) as response:
                    if response.status_code == 416:  # Range Not Satisfiable -> complete or stale
                        downloaded = 0
                        headers.pop("Range", None)
                        mode = "wb"
                        response = await client.get(source_url)
                    elif response.status_code in (200, 206):
                        mode = "ab" if response.status_code == 206 else "wb"
                        if response.status_code == 200:
                            downloaded = 0
                    else:
                        response.raise_for_status()

                    content_length = response.headers.get("content-length")
                    total_bytes = (int(content_length) + downloaded) if content_length else -1

                    async with await anyio.open_file(str(part_path), mode) as f:
                        async for chunk in response.aiter_bytes(chunk_size=65536):
                            await f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback:
                                await progress_callback(
                                    model_id, downloaded, max(downloaded, total_bytes)
                                )

            # Atomic rename on completion
            if part_path.exists():
                part_path.replace(dest_path)

        except Exception as exc:
            logger.error("Download failed for '%s': %s", model_id, exc)
            raise DownloadError(f"Download failed for '{model_id}': {exc}") from exc

        checksum_ok = False
        if expected_sha256:
            checksum_ok = self.verify_checksum(dest_path, expected_sha256)
            if not checksum_ok:
                dest_path.unlink(missing_ok=True)
                raise ChecksumError(f"SHA-256 checksum mismatch for downloaded model '{model_id}'.")

        self._auto_register(model_id, dest_path)
        return DownloadResult(
            model_id=model_id,
            success=True,
            path=dest_path,
            bytes_downloaded=dest_path.stat().st_size,
            checksum_verified=checksum_ok,
        )

    async def download_from_huggingface(
        self,
        repo_id: str,
        filename: str,
        *,
        token: str | None = None,
        expected_sha256: str | None = None,
        progress_callback: ProgressCallback | None = None,
        overwrite: bool = False,
    ) -> DownloadResult:
        """Download a file from Hugging Face Hub."""
        url = f"https://huggingface.co/{repo_id}/resolve/main/{filename}"
        model_id = Path(filename).stem
        return await self.download(
            model_id=model_id,
            source_url=url,
            filename=filename,
            expected_sha256=expected_sha256,
            progress_callback=progress_callback,
            overwrite=overwrite,
        )

    def _auto_register(self, model_id: str, path: Path) -> None:
        """Register the downloaded model file into the ModelRegistry if present."""
        if self._registry is not None:
            self._registry.scan(self._models_dir)

    @staticmethod
    def _filename_from_url(url: str, model_id: str) -> str:
        segment = url.rstrip("/").split("/")[-1]
        if segment and "." in segment:
            return segment
        return f"{model_id}.gguf"
