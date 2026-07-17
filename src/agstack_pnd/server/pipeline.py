"""Shared calculation pipeline.

One async entry point used by both the REST ``/calculate`` router and the MCP
``run_forecast`` tool, so the two never drift. Handles:

  * GeoID resolution (grant-aware) or raw lat/lon,
  * weather provider selection ("dpi" reads Pancake weather BITEs; "noaa" uses NOAA),
  * model execution,
  * optional publishing of the risk result back to Pancake as a PEST_DISEASE BITE.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from agstack_pnd.catalog.loader import get_threat
from agstack_pnd.foundation.geo_resolver import GeoResolver
from agstack_pnd.foundation.model_registry import ModelRegistry
from agstack_pnd.foundation.types import FieldLocation, ModelResult
from agstack_pnd.providers.dpi_weather import BiteWeatherProvider
from agstack_pnd.providers.noaa import NOAAProvider
from agstack_pnd.server.config import settings

_registry = ModelRegistry()


class CalculationError(Exception):
    """Raised by the pipeline with a machine-usable ``status`` (HTTP-like)."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


@dataclass
class CalculationInput:
    model_uuid: UUID
    start_date: date
    end_date: date
    geo_id: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    crop: str | None = None
    threat_scientific_name: str | None = None
    parameters: dict | None = None
    field_grant: str | None = None
    weather_provider: str | None = None
    # Publish the result as a PEST_DISEASE BITE to Pancake. None -> use config default.
    publish: bool | None = None


async def _resolve_location(inp: CalculationInput) -> FieldLocation:
    from agstack_pnd.foundation.exceptions import PNDError

    if inp.geo_id:
        resolver = GeoResolver(
            base_url=settings.agstack_registry_url,
            token=settings.agstack_registry_token or None,
            field_grant=inp.field_grant,
        )
        try:
            return await resolver.resolve(inp.geo_id, fetch_wkt=bool(inp.field_grant))
        except PNDError as e:
            raise CalculationError(400, str(e)) from e
    if inp.latitude is not None and inp.longitude is not None:
        return GeoResolver.from_coordinates(inp.latitude, inp.longitude)
    raise CalculationError(400, "Provide geo_id or latitude+longitude")


async def _fetch_weather(inp: CalculationInput, location: FieldLocation, fields: list[str]):
    from agstack_pnd.foundation.exceptions import PNDError

    provider_name = (inp.weather_provider or settings.weather_provider or "noaa").lower()
    try:
        if provider_name == "dpi":
            if not location.geo_id:
                raise CalculationError(
                    400, "DPI weather provider requires a geo_id (weather BITEs are GeoID-keyed)"
                )
            provider = BiteWeatherProvider(
                geo_id=location.geo_id,
                pancake_url=settings.pancake_url,
                token=settings.pancake_token or None,
                field_grant=inp.field_grant,
            )
        else:
            if not settings.noaa_api_token:
                raise CalculationError(503, "NOAA API token not configured")
            provider = NOAAProvider(settings.noaa_api_token)

        return await provider.get_hourly_data(
            location.latitude, location.longitude, inp.start_date, inp.end_date, fields
        )
    except CalculationError:
        raise
    except PNDError as e:
        raise CalculationError(502, f"Weather data error: {e}") from e


async def run_calculation(inp: CalculationInput) -> ModelResult:
    """Resolve location, fetch weather, run the model. Returns a ModelResult."""
    from agstack_pnd.foundation.exceptions import PNDError

    location = await _resolve_location(inp)

    try:
        model = _registry.get_model(inp.model_uuid)
    except PNDError as e:
        raise CalculationError(404, str(e)) from e

    threat = None
    if inp.crop and inp.threat_scientific_name:
        try:
            threat = get_threat(inp.crop, inp.threat_scientific_name)
        except PNDError as e:
            raise CalculationError(404, str(e)) from e

    weather_data = await _fetch_weather(inp, location, model.required_fields())

    try:
        result = model.calculate(weather_data, parameters=inp.parameters, threat=threat)
    except PNDError as e:
        raise CalculationError(422, f"Model error: {e}") from e

    # Stamp provenance so the output is a self-describing DPI artifact.
    result.metadata.setdefault("geo_id", location.geo_id)
    result.metadata.setdefault(
        "weather_provider", (inp.weather_provider or settings.weather_provider or "noaa").lower()
    )
    if inp.crop:
        result.metadata.setdefault("crop", inp.crop)
    if inp.threat_scientific_name:
        result.metadata.setdefault("threat", inp.threat_scientific_name)

    await _maybe_publish(inp, location, result)
    return result


async def _maybe_publish(
    inp: CalculationInput, location: FieldLocation, result: ModelResult
) -> None:
    """Publish the result as a PEST_DISEASE BITE when enabled and a GeoID exists.

    A publish failure is recorded in metadata but never fails the calculation --
    the forecast is valid whether or not it was also persisted to the data plane.
    """
    should_publish = inp.publish if inp.publish is not None else settings.publish_risk_bites
    if not should_publish:
        return
    if not location.geo_id:
        result.metadata["risk_bite_published"] = False
        result.metadata["risk_bite_error"] = "no geo_id to key the risk BITE"
        return

    from agstack_pnd.server.risk_publisher import publish_risk_bite

    try:
        resp = await publish_risk_bite(
            result, location.geo_id, settings.pancake_url, settings.pancake_token or None
        )
        result.metadata["risk_bite_published"] = True
        result.metadata["risk_bite_id"] = resp.get("bite_id")
    except Exception as e:  # noqa: BLE001 - publishing is best-effort
        result.metadata["risk_bite_published"] = False
        result.metadata["risk_bite_error"] = str(e)
