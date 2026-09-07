"""Local model registry for Atlas OS.

The :class:`ModelRegistry` tracks every AI model known to Atlas — whether
discovered automatically from ``models_dir``, registered programmatically by a
provider, or declared in configuration. It is the *single source of truth*
for model metadata and loaded/unloaded state.

Model state is persisted to a JSON file (e.g. ``data/model_registry.json``)
so that separate CLI processes and service instances read and write consistent state.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from pathlib import Path

from atlas.ai.providers.base import ModelInfo

logger = logging.getLogger(__name__)

# File extensions considered to be model files.
_MODEL_EXTENSIONS = frozenset({".gguf"})


class ModelNotFoundError(Exception):
    """Raised when a requested model is not in the registry."""


class ModelRegistry:
    """Catalog of AI model metadata with disk persistence as single source of truth.

    Persistence is split by *scope* so local (llama.cpp GGUF) and cloud
    model catalogs cannot contaminate each other across processes or test
    runs.  The in-memory model is a single unified dict, but writes go to
    one of two JSON files depending on each entry's ``provider_name``.

    Parameters
    ----------
    persistence_path:
        Explicit JSON file path.  When supplied, that single file is used
        for *all* entries (legacy behaviour).  Mutually exclusive with
        ``data_dir``.
    data_dir:
        Directory under which two scope-specific files are created:
        ``model_registry.local.json`` and ``model_registry.cloud.json``.
        This is the production layout.
    scope:
        When ``"local"`` or ``"cloud"`` is supplied together with
        ``data_dir``, the registry only persists its own scope and ignores
        entries belonging to the other scope (still keeping them in memory
        for the lifetime of this instance).  Default ``"all"`` writes both
        files for its respective scope (cloud entries → cloud file,
        llama_cpp entries → local file).
    """

    _LOCAL_PROVIDER = "llama_cpp"

    def __init__(
        self,
        persistence_path: str | Path | None = None,
        *,
        scope: str = "all",
        data_dir: str | Path | None = None,
    ) -> None:
        if scope not in ("local", "cloud", "all"):
            raise ValueError(
                f"Invalid scope {scope!r}; expected 'local', 'cloud', or 'all'."
            )
        self._scope = scope
        self._models: dict[str, ModelInfo] = {}

        if persistence_path is not None and data_dir is not None:
            raise ValueError(
                "Pass either persistence_path or data_dir, not both."
            )

        if persistence_path is not None:
            # Legacy single-file mode.
            self._split_files: tuple[Path, ...] | None = None
            self._persistence_path: Path | None = Path(persistence_path)
        elif data_dir is not None:
            base = Path(data_dir)
            self._split_files = (
                base / "model_registry.local.json",
                base / "model_registry.cloud.json",
            )
            self._persistence_path = None
        else:
            self._split_files = None
            self._persistence_path = None

        self._load_persistence()
        logger.debug(
            "ModelRegistry initialised (scope=%s, persistence=%s, split=%s).",
            scope, self._persistence_path, self._split_files,
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _file_for(self, info: ModelInfo) -> Path | None:
        """Return the persistence file responsible for *info*, or None for in-memory."""
        if self._persistence_path is not None:
            return self._persistence_path
        if self._split_files is None:
            return None
        local, cloud = self._split_files
        return local if info.provider_name == self._LOCAL_PROVIDER else cloud

    def _load_persistence(self) -> None:
        """Load catalog entries from JSON file(s) if present."""
        if self._persistence_path is not None:
            self._load_from(self._persistence_path)
            return
        if self._split_files is not None:
            for path in self._split_files:
                self._load_from(path)
            return

    def _load_from(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                info = ModelInfo.model_validate(item)
                # Prune local GGUF entries whose file path no longer exists
                is_local = info.provider_name == self._LOCAL_PROVIDER
                is_gguf = "GGUF model at " in info.description
                if is_local and is_gguf:
                    fpath = Path(info.description.replace("GGUF model at ", ""))
                    if not fpath.exists():
                        continue
                self._models[info.model_id] = info
            logger.debug(
                "ModelRegistry: loaded %d model(s) from %s.",
                len(data), path,
            )
        except Exception as exc:
            logger.warning(
                "ModelRegistry: failed to load persistence from %s: %s",
                path, exc,
            )

    def _save_persistence(self) -> None:
        """Save current catalog entries to JSON file(s) per scope."""
        if self._persistence_path is not None:
            self._save_to(
                self._persistence_path,
                [m for m in self._models.values()],
            )
            return
        if self._split_files is None:
            return
        local_path, cloud_path = self._split_files
        local_entries = [m for m in self._models.values()
                         if m.provider_name == self._LOCAL_PROVIDER]
        cloud_entries = [m for m in self._models.values()
                         if m.provider_name != self._LOCAL_PROVIDER]
        self._save_to(local_path, local_entries)
        self._save_to(cloud_path, cloud_entries)

    def _save_to(self, path: Path, entries: list[ModelInfo]) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            data = [m.model_dump(mode="json") for m in entries]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.debug(
                "ModelRegistry: saved %d model(s) to %s.",
                len(entries), path,
            )
        except Exception as exc:
            logger.warning(
                "ModelRegistry: failed to save persistence to %s: %s",
                path, exc,
            )

    # Backwards-compat alias used in some call sites.
    def _save_persistence_to_file(self, path: Path | None = None) -> None:
        """Public hook used by tests; fall back to default save."""
        self._save_persistence()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, info: ModelInfo, *, overwrite: bool = True) -> None:
        """Add or update a model entry."""
        if info.model_id in self._models and not overwrite:
            logger.debug("ModelRegistry: skipping duplicate model '%s'.", info.model_id)
            return
        self._models[info.model_id] = info
        self._save_persistence()
        logger.debug(
            "ModelRegistry: registered model '%s' from provider '%s'.",
            info.model_id,
            info.provider_name,
        )

    def unregister(self, model_id: str) -> None:
        """Remove a model from the registry."""
        if model_id not in self._models:
            raise ModelNotFoundError(model_id)
        del self._models[model_id]
        self._save_persistence()
        logger.debug("ModelRegistry: unregistered model '%s'.", model_id)

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def scan(self, models_dir: str | Path) -> list[ModelInfo]:
        """Scan *models_dir* for model files and register them, preserving loaded state."""
        directory = Path(models_dir)
        discovered: list[ModelInfo] = []
        found_ids: set[str] = set()

        if not directory.exists():
            logger.debug("ModelRegistry.scan: directory %s does not exist.", directory)
            # Prune missing local models
            to_remove = [
                mid for mid, m in self._models.items()
                if m.provider_name == self._LOCAL_PROVIDER
            ]
            for mid in to_remove:
                del self._models[mid]
            if to_remove:
                self._save_persistence()
            return discovered

        for path in sorted(directory.rglob("*")):
            if path.suffix.lower() not in _MODEL_EXTENSIONS:
                continue
            model_id = path.stem
            found_ids.add(model_id)
            size = path.stat().st_size if path.is_file() else -1

            existing = self._models.get(model_id)
            loaded_state = existing.loaded if existing else False

            info = ModelInfo(
                model_id=model_id,
                display_name=model_id.replace("-", " ").replace("_", " ").title(),
                provider_name="llama_cpp",
                loaded=loaded_state,
                size_bytes=size,
                description=f"GGUF model at {path}",
            )
            self._models[model_id] = info
            discovered.append(info)
            logger.info("ModelRegistry: discovered '%s' (%d bytes).", model_id, size)

        # Prune local entries whose files no longer exist
        to_prune = [
            mid for mid, m in self._models.items()
            if m.provider_name == self._LOCAL_PROVIDER and mid not in found_ids
        ]
        for mid in to_prune:
            del self._models[mid]
            logger.debug("ModelRegistry: pruned missing local model '%s'.", mid)

        self._save_persistence()
        return discovered


    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, model_id: str) -> ModelInfo:
        """Return model metadata by ID."""
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
        """Mark *model_id* as loaded in memory."""
        info = self.get(model_id)
        self._models[model_id] = info.model_copy(update={"loaded": True})
        self._save_persistence()
        logger.debug("ModelRegistry: '%s' marked as loaded.", model_id)

    def mark_unloaded(self, model_id: str) -> None:
        """Mark *model_id* as unloaded."""
        info = self.get(model_id)
        self._models[model_id] = info.model_copy(update={"loaded": False})
        self._save_persistence()
        logger.debug("ModelRegistry: '%s' marked as unloaded.", model_id)

    def __repr__(self) -> str:
        loaded = sum(1 for m in self._models.values() if m.loaded)
        return f"ModelRegistry(total={len(self._models)}, loaded={loaded})"
