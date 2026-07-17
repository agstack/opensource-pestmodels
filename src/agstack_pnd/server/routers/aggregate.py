"""Aggregation endpoint -- distinct-field risk statistics."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, model_validator

from agstack_pnd.server.aggregation import aggregate_risk
from agstack_pnd.server.config import settings

router = APIRouter(tags=["aggregate"])


class AggregateRequest(BaseModel):
    geoids: list[str] | None = None
    parent_geo_id: str | None = None

    @model_validator(mode="after")
    def _require_target(self) -> AggregateRequest:
        if not self.geoids and not self.parent_geo_id:
            raise ValueError("Provide geoids or parent_geo_id")
        return self


@router.post("/aggregate")
async def aggregate(req: AggregateRequest) -> dict:
    try:
        return await aggregate_risk(
            pancake_url=settings.pancake_url,
            registry_url=settings.agstack_registry_url,
            geoids=req.geoids,
            parent_geo_id=req.parent_geo_id,
            token=settings.pancake_token or None,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Aggregation failed: {e}") from e
