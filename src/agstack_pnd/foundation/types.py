"""Shared Pydantic models and type definitions."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from agstack_pnd.foundation.engine_params import EngineParamsBase
    from agstack_pnd.foundation.model_registry import ModelRegistry


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ModelLayer(str, Enum):
    WEATHER = "weather"
    AGRONOMIC = "agronomic"
    DISEASE = "disease"


class RiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatType(str, Enum):
    FUNGUS = "fungus"
    BACTERIUM = "bacterium"
    OOMYCETE = "oomycete"
    INSECT = "insect"
    MITE = "mite"


# ---------------------------------------------------------------------------
# Weather data
# ---------------------------------------------------------------------------

STANDARD_WEATHER_FIELDS: list[str] = [
    "air_temperature",
    "air_temperature_min",
    "air_temperature_max",
    "relative_humidity",
    "dew_point",
    "wind_speed",
    "precipitation",
    "solar_radiation",
    "atmospheric_pressure",
]


class WeatherDataFrame:
    """Tabular weather data with standardized field names.

    Backed by a dict of numpy arrays (one per field), all sharing the same
    length (number of hourly or daily observations) and a parallel timestamps
    array.
    """

    def __init__(
        self,
        timestamps: NDArray[np.datetime64],
        fields: dict[str, NDArray[np.floating[Any]]],
    ) -> None:
        n = len(timestamps)
        for name, arr in fields.items():
            if len(arr) != n:
                raise ValueError(
                    f"Field '{name}' has {len(arr)} rows but timestamps has {n}"
                )
        self.timestamps = timestamps
        self.fields = fields

    @property
    def length(self) -> int:
        return len(self.timestamps)

    def __contains__(self, field: str) -> bool:
        return field in self.fields

    def __getitem__(self, field: str) -> NDArray[np.floating[Any]]:
        return self.fields[field]

    def field_names(self) -> list[str]:
        return list(self.fields.keys())


# ---------------------------------------------------------------------------
# Model metadata
# ---------------------------------------------------------------------------

class ModelMetadata(BaseModel):
    """Immutable metadata for a registered pest/disease model."""

    uuid: UUID
    name: str
    display_name: str
    version: str
    layer: ModelLayer
    description: str
    supported_crops: list[str] | None = None
    required_weather_fields: list[str]
    dependencies: list[str] = Field(default_factory=list)
    citation: str | None = None
    author: str = "AgStack Foundation"


# ---------------------------------------------------------------------------
# Model results
# ---------------------------------------------------------------------------

class DailyScore(BaseModel):
    date: date
    value: float
    risk_level: RiskLevel | None = None


class ModelResult(BaseModel):
    """Output of a model calculation."""

    model_uuid: UUID
    model_name: str
    computed_at: datetime
    start_date: date
    end_date: date
    daily_scores: list[DailyScore] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Threat definitions
# ---------------------------------------------------------------------------

class FuzzyRule(BaseModel):
    """A single fuzzy rule mapping variable ranges to a risk level."""

    hum_lo: float
    hum_hi: float
    temp_lo: float
    temp_hi: float
    rain_min: float = 0.0
    risk_level: RiskLevel


class BioParams(BaseModel):
    """Biological parameters for an organism-crop pairing."""

    t_base: float = 10.0
    t_lethal_min: float = -5.0
    t_lethal_max: float = 45.0
    t_optimal_min: float = 15.0
    t_optimal_max: float = 30.0
    min_streak: int = 3
    min_wetness_hours_critical: float = 20.0
    min_wetness_hours_high: float = 14.0
    pheno_lo: float | None = None
    pheno_hi: float | None = None
    pheno_frac_lo: float | None = None
    pheno_frac_hi: float | None = None
    pheno_fraction_ref_gdd5: float = 2200.0
    pheno_bbch_start: str | None = None
    pheno_bbch_end: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class ThreatDefinition(BaseModel):
    """Full definition for a specific organism-crop threat pairing."""

    scientific_name: str
    common_name: str
    threat_type: ThreatType
    crop: str
    bio_params: BioParams
    fuzzy_rules: list[FuzzyRule] = Field(default_factory=list)
    special_rules: dict[str, Any] = Field(default_factory=dict)
    # New path: which engine this threat targets, and its typed params (raw here,
    # validated lazily via resolve_engine_params so loading stays registry-free).
    engine_type: str = "fuzzy_mamdani"
    engine_params: dict[str, Any] | None = None

    def resolve_engine_params(self, registry: ModelRegistry) -> EngineParamsBase:
        """Validate and return this threat's typed engine params.

        Uses ``engine_params`` when the catalog entry supplies it; otherwise
        bridges legacy fuzzy rules.
        """
        # Imported lazily to avoid a module-level import cycle with engine_params.
        from agstack_pnd.foundation.engine_params import build_legacy_fuzzy_engine_params

        if self.engine_params is not None:
            schema = registry.get_engine_params_schema(self.engine_type)
            return schema.model_validate({"engine_type": self.engine_type, **self.engine_params})
        return build_legacy_fuzzy_engine_params(
            fuzzy_rules=[r.model_dump() for r in self.fuzzy_rules],
        )


# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------

class FieldLocation(BaseModel):
    """Resolved location for a field (from GeoID or raw coordinates)."""

    latitude: float
    longitude: float
    geo_id: str | None = None
    wkt: str | None = None
