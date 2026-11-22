"""Model downloader for Atlas OS.

:class:`ModelDownloader` handles fetching GGUF (and future format) model files
from remote sources — primarily Hugging Face Hub — and saving them into
``models_dir``.

Downloads use ``httpx`` streaming so the file is written incrementally without
buffering the entire model in RAM.  Progress is emitted via an optional
``progress_callback`` so the CLI, API, and web dashboard can render it
differently.

Design principles
-----------------
* Downloads are async and non-blocking; they can be dispatched into the
  :class:`~atlas.runtime.tasks.BackgroundTaskManager` for long-running pulls.
* Progress is emitted via an optional ``progress_callback`` so the CLI, API,
  and web dashboard can all render it differently.
* The downloader never hardcodes paths — all destinations come from
  ``AtlasConfig.models_dir``.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)

# Type alias for an async progress callback.
ProgressCallback = Callable[[str, int, int], Awaitable[None]]
"""``callback(model_id, bytes_downloaded, total_bytes)``"""


@dataclass
class DownloadResult:
    """Result of a completed (or failed) download attempt.

    Attributes
    ----------
    model_id:
        Identifier of the model that was downloaded.
    success:
        ``True`` if the file was saved successfully.
    path:
        Local path where the file was saved (empty if *success* is False).
    error:
        Human-readable error message if the download failed.
    bytes_downloaded:
        Total bytes saved.
    """

    model_id: str
    success: bool
    path: Path = field(default_factory=Path)
    error: str = ""
    bytes_downloaded: int = 0


class DownloadError(Exception):
    """Raised when a download cannot be completed."""


class ModelDownloader:
    """Downloads model files from remote sources into ``models_dir``.

    Parameters
    ----------
    models_dir:
        Destination directory for downloaded files.
    """

    def __init__(self, models_dir: str | Path = "./models") -> None:
        self._models_dir = Path(models_dir)
        logger.debug("ModelDownloader initialised; target=%s", self._models_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def download(
        self,
        model_id: str,
        source_url: str,
        *,
        filename: str | None = None,
        progress_callback: ProgressCallback | None = None,
        overwrite: bool = False,
    ) -> DownloadResult:
        """Download a model file from *source_url*.

        Parameters
        ----------
        model_id:
            Identifier assigned to this model (used for logging and the
            :class:`~atlas.ai.model.ModelRegistry`).
        source_url:
            Full URL to the GGUF file (Hugging Face Hub raw URL, CDN, etc.).
        filename:
            Override the local filename.  Defaults to the last path segment
            of *source_url* or ``f"{model_id}.gguf"``.
        progress_callback:
            Async callable invoked periodically with
            ``(model_id, bytes_downloaded, total_bytes)``.
            Pass ``None`` to disable progress reporting.
        overwrite:
            If ``False`` (default) and the file already exists, skip the
            download and return a successful result.

        Returns
        -------
        DownloadResult
            Summary of the download; always check ``result.success``.

        Raises
        ------
        DownloadError
            On unrecoverable network or I/O errors.
        """
        dest_filename = filename or self._filename_from_url(source_url, model_id)
        dest_path = self._models_dir / dest_filename

        # Ensure destination directory exists.
        self._models_dir.mkdir(parents=True, exist_ok=True)

        if dest_path.exists() and not overwrite:
            logger.info(
                "ModelDownloader: '%s' already exists at %s; skipping download.",
                model_id,
                dest_path,
            )
            return DownloadResult(
                model_id=model_id,
                success=True,
                path=dest_path,
                bytes_downloaded=dest_path.stat().st_size,
            )

        logger.info(
            "ModelDownloader: downloading '%s' from %s → %s",
            model_id,
            source_url,
            dest_path,
        )

        try:
            result = await self._stream_download(
                model_id=model_id,
                source_url=source_url,
                dest_path=dest_path,
                progress_callback=progress_callback,
            )
        except Exception as exc:
            logger.error(
                "ModelDownloader: download of '%s' failed: %s", model_id, exc
            )
            raise DownloadError(str(exc)) from exc

        if result.success:
            logger.info(
                "ModelDownloader: '%s' saved to %s (%d bytes).",
                model_id,
                dest_path,
                result.bytes_downloaded,
            )

        return result

    async def download_from_huggingface(
        self,
        repo_id: str,
        filename: str,
        *,
        token: str | None = None,
        progress_callback: ProgressCallback | None = None,
        overwrite: bool = False,
    ) -> DownloadResult:
        """Convenience wrapper that constructs a Hugging Face Hub URL.

        Parameters
        ----------
        repo_id:
            HF repository identifier, e.g. ``"TheBloke/Llama-2-7B-GGUF"``.
        filename:
            File within the repo, e.g. ``"llama-2-7b.Q4_K_M.gguf"``.
        token:
            Optional Hugging Face access token for gated models.
        progress_callback:
            See :meth:`download`.
        overwrite:
            See :meth:`download`.
        """
        url = f"https://huggingface.co/{repo_id}/resolve/main/{filename}"
        headers: dict[str, str] = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
            logger.debug("ModelDownloader: HF token provided for gated model.")
        model_id = Path(filename).stem
        return await self.download(
            model_id=model_id,
            source_url=url,
            filename=filename,
            progress_callback=progress_callback,
            overwrite=overwrite,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _stream_download(
        self,
        model_id: str,
        source_url: str,
        dest_path: Path,
        progress_callback: ProgressCallback | None,
    ) -> DownloadResult:
        """Stream *source_url* to *dest_path* using httpx, reporting progress.

        Uses a 1 MiB read chunk so RAM usage stays flat even for multi-GB
        GGUF files.
        """
        import httpx  # already in pyproject.toml dependencies

        CHUNK_SIZE = 1024 * 1024  # 1 MiB per read

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0),
        ) as client:
            async with client.stream("GET", source_url) as response:
                response.raise_for_status()
                total_bytes = int(response.headers.get("content-length", 0))
                downloaded = 0

                with open(dest_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=CHUNK_SIZE):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            await progress_callback(model_id, downloaded, total_bytes)

        return DownloadResult(
            model_id=model_id,
            success=True,
            path=dest_path,
            bytes_downloaded=downloaded,
        )

    @staticmethod
    def _filename_from_url(url: str, model_id: str) -> str:
        """Derive a local filename from *url*, falling back to *model_id*."""
        segment = url.rstrip("/").split("/")[-1]
        if segment and "." in segment:
            return segment
        return f"{model_id}.gguf"

    def __repr__(self) -> str:
        return f"ModelDownloader(models_dir={self._models_dir!r})"
