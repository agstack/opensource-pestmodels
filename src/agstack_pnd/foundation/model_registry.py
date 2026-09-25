"""UUID-based model registry with entry-point auto-discovery."""

from __future__ import annotations

import importlib.metadata
from typing import TYPE_CHECKING
from uuid import UUID

from agstack_pnd.foundation.exceptions import EngineTypeNotFound, ModelNotFound

if TYPE_CHECKING:
    from agstack_pnd.foundation.base_model import PestModelBase
    from agstack_pnd.foundation.engine_params import EngineParamsBase
    from agstack_pnd.foundation.types import ModelLayer, ModelMetadata

ENTRY_POINT_GROUP = "agstack_pnd.models"


class ModelRegistry:
    """Discovers, caches, and serves registered pest/disease models.

    Models register via Python entry points in ``pyproject.toml``::

        [project.entry-points."agstack_pnd.models"]
        my_model = "my_package.module:MyModelClass"

    Third-party packages can register models by shipping a wheel with
    the entry point above.
    """

    def __init__(self) -> None:
        self._models: dict[UUID, type[PestModelBase]] = {}
        self._engine_param_schemas: dict[str, type[EngineParamsBase]] = {}
        self._discovered = False

    def _discover(self) -> None:
        """Load all entry-point-registered model classes."""
        if self._discovered:
            return

        eps = importlib.metadata.entry_points()
        group = eps.select(group=ENTRY_POINT_GROUP) if hasattr(eps, "select") else eps.get(ENTRY_POINT_GROUP, [])

        for ep in group:
            try:
                cls = ep.load()
                if hasattr(cls, "metadata") and hasattr(cls.metadata, "uuid"):
                    self._models[cls.metadata.uuid] = cls
                    self._index_engine_params_schema(cls)
            except Exception:  # noqa: BLE001
                continue

        self._discovered = True

    def _index_engine_params_schema(self, model_cls: type[PestModelBase]) -> None:
        schema = getattr(model_cls, "engine_params_schema", None)
        if schema is None:
            return
        # engine_type is a Literal default on the schema, e.g. "fuzzy_mamdani"
        engine_type = schema.model_fields["engine_type"].default
        self._engine_param_schemas[engine_type] = schema

    def register(self, model_cls: type[PestModelBase]) -> None:
        """Manually register a model class."""
        self._models[model_cls.metadata.uuid] = model_cls
        self._index_engine_params_schema(model_cls)

    def list_models(
        self,
        layer: ModelLayer | None = None,
        crop: str | None = None,
    ) -> list[ModelMetadata]:
        """Return metadata for all registered models, optionally filtered."""
        self._discover()
        results: list[ModelMetadata] = []
        for cls in self._models.values():
            meta = cls.metadata
            if layer and meta.layer != layer:
                continue
            if crop and meta.supported_crops and crop not in meta.supported_crops:
                continue
            results.append(meta)
        return results

    def get_model_class(self, uuid: UUID) -> type[PestModelBase]:
        """Return the model class for a UUID."""
        self._discover()
        if uuid not in self._models:
            raise ModelNotFound(str(uuid))
        return self._models[uuid]

    def get_model(self, uuid: UUID) -> PestModelBase:
        """Instantiate and return a model by UUID."""
        cls = self.get_model_class(uuid)
        return cls()

    def get_by_name(self, name: str) -> PestModelBase:
        """Instantiate a model by its metadata name."""
        self._discover()
        for cls in self._models.values():
            if cls.metadata.name == name:
                return cls()
        raise ModelNotFound(name)

    def get_engine_params_schema(self, engine_type: str) -> type[EngineParamsBase]:
        """Return the typed params schema declared by any model for this engine_type.

        A third-party model registers a new engine_type simply by shipping a
        model class with an ``engine_params_schema`` ClassVar -- no core PR.
        """
        self._discover()
        if engine_type not in self._engine_param_schemas:
            raise EngineTypeNotFound(engine_type)
        return self._engine_param_schemas[engine_type]
