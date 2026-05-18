"""Model discovery and catalog endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException

from agstack_pnd.catalog.crops import get_supported_crops, get_threats_for_crop
from agstack_pnd.catalog.loader import list_threats
from agstack_pnd.foundation.model_registry import ModelRegistry
from agstack_pnd.foundation.types import ModelLayer

router = APIRouter(tags=["models"])
_registry = ModelRegistry()


@router.get("/models")
async def list_models(
    layer: ModelLayer | None = None,
    crop: str | None = None,
) -> list[dict]:
    models = _registry.list_models(layer=layer, crop=crop)
    return [m.model_dump(mode="json") for m in models]


@router.get("/models/{model_uuid}")
async def get_model(model_uuid: UUID) -> dict:
    try:
        cls = _registry.get_model_class(model_uuid)
        return cls.metadata.model_dump(mode="json")
    except Exception:
        raise HTTPException(status_code=404, detail=f"Model {model_uuid} not found")


@router.get("/crops")
async def list_crops() -> list[str]:
    return get_supported_crops()


@router.get("/crops/{crop}/threats")
async def get_crop_threats(crop: str) -> list[dict[str, str]]:
    return get_threats_for_crop(crop)


@router.get("/threats")
async def get_all_threats(crop: str | None = None) -> list[dict]:
    threats = list_threats(crop)
    return [t.model_dump(mode="json") for t in threats]
