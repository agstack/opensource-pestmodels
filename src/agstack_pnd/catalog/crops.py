"""Crop registry -- convenience accessors."""

from __future__ import annotations

from agstack_pnd.catalog.loader import list_crops, list_threats


def get_supported_crops() -> list[str]:
    """Return all crops with at least one threat definition."""
    return list_crops()


def get_threats_for_crop(crop: str) -> list[dict[str, str]]:
    """Return summary of all threats for a given crop."""
    threats = list_threats(crop)
    return [
        {
            "scientific_name": t.scientific_name,
            "common_name": t.common_name,
            "threat_type": t.threat_type.value,
        }
        for t in threats
    ]
