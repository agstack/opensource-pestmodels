"""Calculation endpoints -- run models via the API."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agstack_pnd.server.pipeline import CalculationError, CalculationInput, run_calculation

router = APIRouter(tags=["calculate"])


class CalculateRequest(BaseModel):
    model_uuid: UUID
    geo_id: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    crop: str | None = None
    threat_scientific_name: str | None = None
    start_date: date
    end_date: date
    parameters: dict | None = None
    # Optional AR2 field grant (SD-JWT VC); forwarded to the registry + Pancake.
    field_grant: str | None = None
    # Per-request weather provider override ("dpi" | "noaa"); defaults to config.
    weather_provider: str | None = None


@router.post("/calculate")
async def calculate(req: CalculateRequest) -> dict:
    inp = CalculationInput(
        model_uuid=req.model_uuid,
        start_date=req.start_date,
        end_date=req.end_date,
        geo_id=req.geo_id,
        latitude=req.latitude,
        longitude=req.longitude,
        crop=req.crop,
        threat_scientific_name=req.threat_scientific_name,
        parameters=req.parameters,
        field_grant=req.field_grant,
        weather_provider=req.weather_provider,
    )
    try:
        result = await run_calculation(inp)
    except CalculationError as e:
        raise HTTPException(status_code=e.status, detail=e.detail) from e

    return result.model_dump(mode="json")
