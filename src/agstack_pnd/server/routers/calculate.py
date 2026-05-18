"""Calculation endpoints -- run models via the API."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agstack_pnd.catalog.loader import get_threat
from agstack_pnd.foundation.exceptions import PNDError
from agstack_pnd.foundation.geo_resolver import GeoResolver
from agstack_pnd.foundation.model_registry import ModelRegistry
from agstack_pnd.foundation.types import ModelResult
from agstack_pnd.providers.noaa import NOAAProvider
from agstack_pnd.server.config import settings

router = APIRouter(tags=["calculate"])
_registry = ModelRegistry()


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


@router.post("/calculate")
async def calculate(req: CalculateRequest) -> dict:
    # Resolve location
    if req.geo_id:
        resolver = GeoResolver(token=settings.agstack_registry_token or None)
        try:
            location = await resolver.resolve(req.geo_id)
        except PNDError as e:
            raise HTTPException(status_code=400, detail=str(e))
    elif req.latitude is not None and req.longitude is not None:
        location = GeoResolver.from_coordinates(req.latitude, req.longitude)
    else:
        raise HTTPException(status_code=400, detail="Provide geo_id or latitude+longitude")

    # Get model
    try:
        model = _registry.get_model(req.model_uuid)
    except PNDError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Get threat definition if this is a disease model
    threat = None
    if req.crop and req.threat_scientific_name:
        try:
            threat = get_threat(req.crop, req.threat_scientific_name)
        except PNDError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # Fetch weather
    if not settings.noaa_api_token:
        raise HTTPException(status_code=503, detail="NOAA API token not configured")

    provider = NOAAProvider(settings.noaa_api_token)
    try:
        weather_data = await provider.get_hourly_data(
            location.latitude,
            location.longitude,
            req.start_date,
            req.end_date,
            model.required_fields(),
        )
    except PNDError as e:
        raise HTTPException(status_code=502, detail=f"Weather data error: {e}")

    # Run model
    try:
        result: ModelResult = model.calculate(
            weather_data,
            parameters=req.parameters,
            threat=threat,
        )
    except PNDError as e:
        raise HTTPException(status_code=422, detail=f"Model error: {e}")

    return result.model_dump(mode="json")
