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

mcp = FastMCP(
    "AgStack PND",
    description="Hierarchical pest and disease models for agriculture",
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
