"""RH/rainfall-based leaf wetness estimation.

Lookup-table approach based on relative humidity thresholds and rainfall additive.

Citations:
- Pedro & Gillespie (1982). Estimating dew duration. Theoretical and Applied
  Climatology, 30, 109-120.
- Sentelhas, Gillespie, Gleason, et al. (2008). Evaluation of a Penman-Monteith
  approach to provide estimates of leaf wetness duration. Agricultural and Forest
  Meteorology, 148(11), 1680-1689.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import ClassVar
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

# RH threshold -> estimated wetness hours per day
_RH_THRESHOLDS: list[tuple[float, float]] = [
    (95.0, 20.0),
    (85.0, 14.0),
    (75.0, 8.0),
    (65.0, 4.0),
]

# Rainfall (mm/day) -> additive wetness hours
_RAIN_ADDITIVE: list[tuple[float, float]] = [
    (5.0, 6.0),
    (1.0, 4.0),
    (0.1, 2.0),
]

_MAX_WET_HOURS = 24.0


class LeafWetnessRH(PestModelBase):
    """Leaf wetness estimation from daily RH and rainfall.

    Uses lookup tables: RH >= 95% -> 20h, >= 85% -> 14h, >= 75% -> 8h,
    >= 65% -> 4h. Rainfall adds: >= 5mm -> +6h, >= 1mm -> +4h, >= 0.1mm -> +2h.
    Capped at 24h/day.
    """

    metadata: ClassVar[ModelMetadata] = ModelMetadata(
        uuid=UUID("a1b2c3d4-0003-4000-8000-000000000002"),
        name="leaf_wetness_rh",
        display_name="Leaf Wetness (RH/Rainfall Lookup)",
        version="2.0.0",
        layer=ModelLayer.AGRONOMIC,
        description="Estimates daily leaf wetness hours from RH thresholds and rainfall additive.",
        supported_crops=None,
        required_weather_fields=["relative_humidity", "precipitation"],
        citation="Pedro & Gillespie (1982); Sentelhas et al. (2008).",
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

        rh = weather_data["relative_humidity"]
        precip = weather_data["precipitation"]
        ts = weather_data.timestamps

        unique_dates = np.unique(ts.astype("datetime64[D]"))
        daily_scores: list[DailyScore] = []

        for day in unique_dates:
            mask = ts.astype("datetime64[D]") == day
            rh_max = float(np.max(rh[mask])) if np.any(mask) else 0.0
            rain_total = float(np.sum(precip[mask]))

            base_hours = 0.0
            for threshold, hours in _RH_THRESHOLDS:
                if rh_max >= threshold:
                    base_hours = hours
                    break

            rain_hours = 0.0
            for threshold, hours in _RAIN_ADDITIVE:
                if rain_total >= threshold:
                    rain_hours = hours
                    break

            wet_hours = min(base_hours + rain_hours, _MAX_WET_HOURS)
            daily_scores.append(DailyScore(
                date=day.astype("datetime64[D]").astype(object),
                value=wet_hours,
            ))

        total = sum(s.value for s in daily_scores)
        return ModelResult(
            model_uuid=self.metadata.uuid,
            model_name=self.metadata.name,
            computed_at=datetime.now(tz=timezone.utc),
            start_date=daily_scores[0].date if daily_scores else unique_dates[0].astype(object),
            end_date=daily_scores[-1].date if daily_scores else unique_dates[-1].astype(object),
            daily_scores=daily_scores,
            summary={"total_wet_hours": total, "days": len(daily_scores)},
        )
