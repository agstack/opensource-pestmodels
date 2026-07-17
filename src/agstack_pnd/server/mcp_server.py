"""MCP server -- Model Context Protocol for AI agent integration.

Exposes pest/disease models as MCP tools via Streamable HTTP transport.
Mounted on the FastAPI app at /mcp.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from mcp.server.fastmcp import FastMCP

from agstack_pnd.catalog.crops import get_supported_crops, get_threats_for_crop
from agstack_pnd.catalog.loader import get_threat, list_threats
from agstack_pnd.foundation.model_registry import ModelRegistry
from agstack_pnd.server.aggregation import aggregate_risk
from agstack_pnd.server.config import settings
from agstack_pnd.server.pipeline import CalculationError, CalculationInput, run_calculation

mcp = FastMCP(
    "AgStack PND",
    instructions="Hierarchical pest and disease models for agriculture",
)

_registry = ModelRegistry()


@mcp.tool()
def list_pest_models(
    layer: str | None = None,
    crop: str | None = None,
) -> list[dict]:
    """List all available pest and disease models.

    Filter by layer ('weather', 'agronomic', 'disease') or crop name.
    Returns model UUIDs, names, descriptions, and supported crops.
    """
    from agstack_pnd.foundation.types import ModelLayer

    ml = ModelLayer(layer) if layer else None
    models = _registry.list_models(layer=ml, crop=crop)
    return [m.model_dump(mode="json") for m in models]


@mcp.tool()
def get_model_info(model_uuid: str) -> dict:
    """Get detailed metadata and parameter schema for a model by UUID."""
    cls = _registry.get_model_class(UUID(model_uuid))
    return cls.metadata.model_dump(mode="json")


@mcp.tool()
def get_supported_crops_tool() -> list[str]:
    """List all crops that have pest/disease models available."""
    return get_supported_crops()


@mcp.tool()
def get_threats_for_crop_tool(crop: str) -> list[dict]:
    """List all pest and disease threats for a specific crop.

    Returns scientific names, common names, and threat types.
    """
    return get_threats_for_crop(crop)


@mcp.tool()
def explain_threat(crop: str, scientific_name: str) -> dict:
    """Get detailed biological parameters for a specific crop-threat pairing.

    Includes optimal temperatures, lethal thresholds, phenology windows,
    and any special rules (e.g., Mills table, Goidanich rule).
    """
    threat = get_threat(crop, scientific_name)
    return threat.model_dump(mode="json")


@mcp.tool()
async def run_forecast(
    model_uuid: str,
    start_date: str,
    end_date: str,
    geo_id: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    crop: str | None = None,
    threat_scientific_name: str | None = None,
    field_grant: str | None = None,
    weather_provider: str | None = None,
    publish: bool | None = None,
) -> dict:
    """Run a pest/disease forecast for a field and return the risk result.

    Provide either a ``geo_id`` (resolved via the AgStack registry) or raw
    ``latitude``/``longitude``. For a disease model, also pass ``crop`` and
    ``threat_scientific_name``. ``weather_provider`` may be "dpi" (read weather
    BITEs from Pancake) or "noaa"; it defaults to the server configuration.
    Supply ``field_grant`` (an AR2 SD-JWT credential) to authorize L1 access and
    grant-gated weather. Set ``publish`` to persist the result as a PEST_DISEASE
    BITE. This is the agent-callable equivalent of POST /api/v1/calculate.
    """
    inp = CalculationInput(
        model_uuid=UUID(model_uuid),
        start_date=date.fromisoformat(start_date),
        end_date=date.fromisoformat(end_date),
        geo_id=geo_id,
        latitude=latitude,
        longitude=longitude,
        crop=crop,
        threat_scientific_name=threat_scientific_name,
        field_grant=field_grant,
        weather_provider=weather_provider,
        publish=publish,
    )
    try:
        result = await run_calculation(inp)
    except CalculationError as e:
        return {"error": e.detail, "status": e.status}
    return result.model_dump(mode="json")


@mcp.tool()
async def aggregate_risk_tool(
    geoids: list[str] | None = None,
    parent_geo_id: str | None = None,
) -> dict:
    """Aggregate published risk over a distinct set of fields.

    Give an explicit ``geoids`` list or a ``parent_geo_id`` (expanded into its
    nested child fields when the registry exposes them). Returns distinct-field
    counts and the percentage of fields at high/critical risk -- the kind of
    population statistic that is only correct because AR2 de-duplicates fields.
    """
    return await aggregate_risk(
        pancake_url=settings.pancake_url,
        registry_url=settings.agstack_registry_url,
        geoids=geoids,
        parent_geo_id=parent_geo_id,
        token=settings.pancake_token or None,
    )


@mcp.resource("pnd://models")
def models_resource() -> str:
    """Full catalog of all registered pest/disease models."""
    models = _registry.list_models()
    lines = [f"# AgStack PND Model Catalog ({len(models)} models)\n"]
    for m in models:
        lines.append(f"## {m.display_name}")
        lines.append(f"- UUID: {m.uuid}")
        lines.append(f"- Layer: {m.layer.value}")
        lines.append(f"- Crops: {', '.join(m.supported_crops) if m.supported_crops else 'all'}")
        lines.append(f"- Description: {m.description}")
        lines.append("")
    return "\n".join(lines)


@mcp.resource("pnd://crops")
def crops_resource() -> str:
    """Supported crops and their threat counts."""
    crops = get_supported_crops()
    lines = [f"# Supported Crops ({len(crops)})\n"]
    for crop in crops:
        threats = list_threats(crop)
        lines.append(f"- **{crop}**: {len(threats)} threats")
    return "\n".join(lines)
