"""Load threat catalog from bundled JSON seed data."""

from __future__ import annotations

import json
from pathlib import Path

from agstack_pnd.foundation.exceptions import ThreatNotFound
from agstack_pnd.foundation.types import BioParams, FuzzyRule, RiskLevel, ThreatDefinition, ThreatType

_CATALOG_PATH = Path(__file__).parent / "data" / "pest_catalog.json"
_cache: list[ThreatDefinition] | None = None


def _load_catalog() -> list[ThreatDefinition]:
    global _cache  # noqa: PLW0603
    if _cache is not None:
        return _cache

    with open(_CATALOG_PATH) as f:
        raw = json.load(f)

    threats: list[ThreatDefinition] = []
    for entry in raw:
        bio = entry.get("bio_params", {})
        rules_raw = entry.get("fuzzy_rules", [])
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
        threats.append(ThreatDefinition(
            scientific_name=entry["scientific_name"],
            common_name=entry["common_name"],
            threat_type=ThreatType(entry.get("threat_type", "fungus")),
            crop=entry["crop"],
            bio_params=BioParams(**bio),
            fuzzy_rules=fuzzy_rules,
            special_rules=entry.get("special_rules", {}),
        ))

    _cache = threats
    return _cache


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
