"""Local model registry for Atlas OS.

The :class:`ModelRegistry` tracks every AI model known to Atlas — whether
discovered automatically from ``models_dir``, registered programmatically by a
provider, or declared in configuration.  It is the *single source of truth*
for model metadata and loaded/unloaded state.

For Phase 5, the registry is purely in-memory.  Persistence to a JSON catalog
file is deferred to Phase 6 without any interface change.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator

from atlas.ai.providers.base import ModelInfo

logger = logging.getLogger(__name__)

# File extensions considered to be model files.
_MODEL_EXTENSIONS = frozenset({".gguf"})


class ModelNotFoundError(Exception):
    """Raised when a requested model is not in the registry."""


class ModelRegistry:
    """In-memory catalog of AI model metadata.

    The registry merges information from multiple sources:

    1. **File-system scan** — :meth:`scan` walks ``models_dir`` and registers
       any ``.gguf`` files it finds.
    2. **Provider registration** — providers call :meth:`register` to add
       their models (including cloud models with no on-disk file).
    3. **State updates** — :meth:`mark_loaded` / :meth:`mark_unloaded` track
       run-time state so ``atlas model list`` can show what is hot.
    """

    def __init__(self) -> None:
        self._models: dict[str, ModelInfo] = {}
        logger.debug("ModelRegistry initialised.")

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, info: ModelInfo, *, overwrite: bool = True) -> None:
        """Add or update a model entry.

        Parameters
        ----------
        info:
            Metadata to store.
        overwrite:
            If ``True`` (default), replace any existing entry with the same
            ``model_id``.  If ``False``, silently skip duplicates.
        """
        if info.model_id in self._models and not overwrite:
            logger.debug("ModelRegistry: skipping duplicate model '%s'.", info.model_id)
            return
        self._models[info.model_id] = info
        logger.debug(
            "ModelRegistry: registered model '%s' from provider '%s'.",
            info.model_id,
            info.provider_name,
        )

    def unregister(self, model_id: str) -> None:
        """Remove a model from the registry.

        Raises
        ------
        ModelNotFoundError
        """
        if model_id not in self._models:
            raise ModelNotFoundError(model_id)
        del self._models[model_id]
        logger.debug("ModelRegistry: unregistered model '%s'.", model_id)

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def scan(self, models_dir: str | Path) -> list[ModelInfo]:
        """Scan *models_dir* for model files and register them.

        Only ``.gguf`` files are recognised for now; more extensions can be
        added to ``_MODEL_EXTENSIONS`` as new backends land.

        Parameters
        ----------
        models_dir:
            Directory to scan recursively.

        Returns
        -------
        list[ModelInfo]
            Newly discovered models (already registered in ``self``).
        """
        directory = Path(models_dir)
        discovered: list[ModelInfo] = []

        if not directory.exists():
            logger.debug("ModelRegistry.scan: directory %s does not exist.", directory)
            return discovered

        for path in sorted(directory.rglob("*")):
            if path.suffix.lower() not in _MODEL_EXTENSIONS:
                continue
            model_id = path.stem
            size = path.stat().st_size if path.is_file() else -1
            info = ModelInfo(
                model_id=model_id,
                display_name=model_id.replace("-", " ").replace("_", " ").title(),
                provider_name="llama_cpp",
                loaded=self._models.get(model_id, ModelInfo(
                    model_id=model_id, display_name="", provider_name="llama_cpp"
                )).loaded,
                size_bytes=size,
                description=f"GGUF model at {path}",
            )
            self.register(info)
            discovered.append(info)
            logger.info("ModelRegistry: discovered '%s' (%d bytes).", model_id, size)

        return discovered

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, model_id: str) -> ModelInfo:
        """Return model metadata by ID.

        Raises
        ------
        ModelNotFoundError
        """
        try:
            return self._models[model_id]
        except KeyError:
            raise ModelNotFoundError(
                f"Model '{model_id}' is not in the registry. "
                f"Available: {self.model_ids()}"
            ) from None

    def list_all(self) -> list[ModelInfo]:
        """Return all registered models sorted alphabetically by ID."""
        return sorted(self._models.values(), key=lambda m: m.model_id)

    def list_loaded(self) -> list[ModelInfo]:
        """Return only models currently marked as loaded."""
        return [m for m in self._models.values() if m.loaded]

    def model_ids(self) -> list[str]:
        """Return all known model IDs."""
        return sorted(self._models)

    def __contains__(self, model_id: str) -> bool:
        return model_id in self._models

    def __len__(self) -> int:
        return len(self._models)

    def __iter__(self) -> Iterator[ModelInfo]:
        return iter(self.list_all())

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def mark_loaded(self, model_id: str) -> None:
        """Mark *model_id* as loaded in memory.

        Raises
        ------
        ModelNotFoundError
        """
        info = self.get(model_id)
        self._models[model_id] = info.model_copy(update={"loaded": True})
        logger.debug("ModelRegistry: '%s' marked as loaded.", model_id)

    def mark_unloaded(self, model_id: str) -> None:
        """Mark *model_id* as unloaded.

        Raises
        ------
        ModelNotFoundError
        """
        info = self.get(model_id)
        self._models[model_id] = info.model_copy(update={"loaded": False})
        logger.debug("ModelRegistry: '%s' marked as unloaded.", model_id)

    def __repr__(self) -> str:
        loaded = sum(1 for m in self._models.values() if m.loaded)
        return f"ModelRegistry(total={len(self._models)}, loaded={loaded})"
