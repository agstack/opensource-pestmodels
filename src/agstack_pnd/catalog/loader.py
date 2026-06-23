"""Load threat catalog from bundled JSON seed data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from agstack_pnd.foundation.exceptions import ThreatNotFound
from agstack_pnd.foundation.types import (
    BioParams,
    FuzzyRule,
    RiskLevel,
    ThreatDefinition,
    ThreatType,
)

_CATALOG_PATH = Path(__file__).parent / "data" / "pest_catalog.json"
_BATCH_CATALOG_PATH = Path(__file__).parent / "data" / "pest_catalog_batch.json"
_state: dict[str, list[ThreatDefinition] | None] = {"cache": None}


def _parse_entry(entry: dict[str, Any]) -> ThreatDefinition:
    bio = cast("dict[str, Any]", entry.get("bio_params", {}))
    rules_raw = cast("list[dict[str, Any]]", entry.get("fuzzy_rules", []))
    fuzzy_rules = [
        FuzzyRule(
            hum_lo=r["hum_lo"],
            hum_hi=r["hum_hi"],
            temp_lo=r["temp_lo"],
            temp_hi=r["temp_hi"],
            rain_min=r.get("rain_min", 0.0),
            risk_level=RiskLevel(r["risk_level"]),
        )
        for r in rules_raw
    ]
    return ThreatDefinition(
        scientific_name=cast("str", entry["scientific_name"]),
        common_name=cast("str", entry["common_name"]),
        threat_type=ThreatType(entry.get("threat_type", "fungus")),
        crop=cast("str", entry["crop"]),
        bio_params=BioParams(**bio),
        fuzzy_rules=fuzzy_rules,
        special_rules=cast("dict[str, Any]", entry.get("special_rules", {})),
    )


def _load_catalog() -> list[ThreatDefinition]:
    cache = _state["cache"]
    if cache is not None:
        return cache

    catalog_paths = [_CATALOG_PATH]
    if _BATCH_CATALOG_PATH.exists():
        catalog_paths.append(_BATCH_CATALOG_PATH)

    merged: dict[tuple[str, str], ThreatDefinition] = {}
    for path in catalog_paths:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        for entry in raw:
            threat = _parse_entry(entry)
            key = (threat.crop.lower(), threat.scientific_name.lower())
            merged[key] = threat

    cache = list(merged.values())
    _state["cache"] = cache
    return cache


def list_crops() -> list[str]:
    """Return sorted list of all crops in the catalog."""
    catalog = _load_catalog()
    return sorted({t.crop for t in catalog})


def list_threats(crop: str | None = None) -> list[ThreatDefinition]:
    """Return all threat definitions, optionally filtered by crop."""
    catalog = _load_catalog()
    if crop:
        return [t for t in catalog if t.crop.lower() == crop.lower()]
    return list(catalog)


def get_threat(crop: str, scientific_name: str) -> ThreatDefinition:
    """Look up a specific crop-threat pairing."""
    catalog = _load_catalog()
    for t in catalog:
        if t.crop.lower() == crop.lower() and t.scientific_name.lower() == scientific_name.lower():
            return t
    raise ThreatNotFound(crop, scientific_name)
