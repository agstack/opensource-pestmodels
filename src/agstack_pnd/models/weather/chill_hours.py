"""Chill Hours models -- Utah and 32-45 variants.

Consolidated from the legacy duplicated ChillDictModel pattern.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, ClassVar
from uuid import UUID

import numpy as np

from agstack_pnd.foundation.base_model import PestModelBase
from agstack_pnd.foundation.types import (
    DailyScore,
    ModelLayer,
    ModelMetadata,
    ModelResult,
    ThreatDefinition,
    WeatherDataFrame,
)

# Temperature ranges are in Fahrenheit for chill models (standard in dormancy literature)


def _celsius_to_fahrenheit(t: float) -> float:
    return t * 1.8 + 32.0


def _chill_increment(temp_f: float, table: dict[str, float]) -> float:
    """Look up the chill increment for a temperature using a range table.

    Keys are either 'lt_N', 'gt_N', or 'N_M' (range N to M inclusive).
    """
    for key, increment in table.items():
        if key.startswith("lt_"):
            threshold = float(key[3:])
            if temp_f < threshold:
                return increment
        elif key.startswith("gt_"):
            threshold = float(key[3:])
            if temp_f > threshold:
                return increment
        elif "_" in key:
            parts = key.split("_")
            lo, hi = float(parts[0]), float(parts[1])
            if lo <= temp_f <= hi:
                return increment
    return 0.0


# Utah model: Richardson et al. (1974)
UTAH_TABLE: dict[str, float] = {
    "lt_34": 0.0,
    "34_36": 0.5,
    "36_48": 1.0,
    "48_54": 0.5,
    "54_60": 0.0,
    "60_65": -0.5,
    "gt_65": -1.0,
}

# 32-45 simplified model
TABLE_3245: dict[str, float] = {
    "lt_32": 0.0,
    "32_45": 1.0,
    "gt_45": 0.0,
}


class ChillHoursUtah(PestModelBase):
    """Utah Chill Hours model.

    Assigns fractional chill units per hour based on temperature ranges.
    Negative units above 60F reflect de-chilling.

    Citation: Richardson, Seeley & Walker (1974). A model for estimating
    the completion of rest for Redhaven and Elberta peach trees.
    HortScience, 9(4), 331-332.
    """

    metadata: ClassVar[ModelMetadata] = ModelMetadata(
        uuid=UUID("a1b2c3d4-0002-4000-8000-000000000001"),
        name="chill_hours_utah",
        display_name="Chill Hours (Utah Model)",
        version="2.0.0",
        layer=ModelLayer.WEATHER,
        description="Utah chill unit accumulation with fractional and negative weighting.",
        supported_crops=None,
        required_weather_fields=["air_temperature"],
        citation="Richardson, Seeley & Walker (1974). HortScience, 9(4), 331-332.",
        author="AgStack Foundation",
    )

    def validate_parameters(self, parameters: dict[str, object] | None) -> dict[str, object]:
        return dict(parameters) if parameters else {}

    def calculate(
        self,
        weather_data: WeatherDataFrame,
        parameters: dict[str, object] | None = None,
        threat: ThreatDefinition | None = None,
    ) -> ModelResult:
        self.validate_parameters(parameters)
        return _compute_chill(weather_data, UTAH_TABLE, self.metadata)


class ChillHours3245(PestModelBase):
    """Simplified 32-45F chill hours model.

    Awards 1 chill unit per hour when temperature is between 32-45F.
    """

    metadata: ClassVar[ModelMetadata] = ModelMetadata(
        uuid=UUID("a1b2c3d4-0002-4000-8000-000000000002"),
        name="chill_hours_3245",
        display_name="Chill Hours (32-45F Model)",
        version="2.0.0",
        layer=ModelLayer.WEATHER,
        description="Simple binary chill accumulation for hours between 32-45F.",
        supported_crops=None,
        required_weather_fields=["air_temperature"],
        author="AgStack Foundation",
    )

    def validate_parameters(self, parameters: dict[str, object] | None) -> dict[str, object]:
        return dict(parameters) if parameters else {}

    def calculate(
        self,
        weather_data: WeatherDataFrame,
        parameters: dict[str, object] | None = None,
        threat: ThreatDefinition | None = None,
    ) -> ModelResult:
        self.validate_parameters(parameters)
        return _compute_chill(weather_data, TABLE_3245, self.metadata)


def _compute_chill(
    weather_data: WeatherDataFrame,
    table: dict[str, float],
    meta: ModelMetadata,
) -> ModelResult:
    temps_c = weather_data["air_temperature"]
    ts = weather_data.timestamps

    unique_dates = np.unique(ts.astype("datetime64[D]"))
    daily_scores: list[DailyScore] = []
    cumulative = 0.0

    for day in unique_dates:
        mask = ts.astype("datetime64[D]") == day
        day_temps = temps_c[mask]
        day_chill = sum(
            _chill_increment(_celsius_to_fahrenheit(float(t)), table)
            for t in day_temps
        )
        cumulative += day_chill
        daily_scores.append(DailyScore(
            date=day.astype("datetime64[D]").astype(object),
            value=round(cumulative, 2),
        ))

    return ModelResult(
        model_uuid=meta.uuid,
        model_name=meta.name,
        computed_at=datetime.now(tz=timezone.utc),
        start_date=daily_scores[0].date if daily_scores else unique_dates[0].astype(object),
        end_date=daily_scores[-1].date if daily_scores else unique_dates[-1].astype(object),
        daily_scores=daily_scores,
        summary={"total_chill_units": round(cumulative, 2), "days": len(daily_scores)},
    )
