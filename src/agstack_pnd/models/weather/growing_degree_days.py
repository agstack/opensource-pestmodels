"""Growing Degree Days (GDD) -- multi-base temperature accumulation model."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, ClassVar
from uuid import UUID

import numpy as np

from agstack_pnd.foundation.base_model import PestModelBase
from agstack_pnd.foundation.exceptions import ModelValidationError
from agstack_pnd.foundation.types import (
    DailyScore,
    ModelLayer,
    ModelMetadata,
    ModelResult,
    ThreatDefinition,
    WeatherDataFrame,
)

_DEFAULT_BASE_TEMP = 10.0  # Celsius
_DEFAULT_UPPER_THRESHOLD = 50.0  # Celsius


class GrowingDegreeDays(PestModelBase):
    """Calculates Growing Degree Days: GDD = max(0, T_avg - T_base) per day.

    Supports configurable base temperature (default 10C) and optional upper
    threshold for capping. Commonly used bases: 0C, 5C, 10C, or pest-specific.

    Citation: McMaster & Wilhelm (1997). Growing degree-days: one equation,
    two interpretations. Agricultural and Forest Meteorology, 87(4), 291-300.
    """

    metadata: ClassVar[ModelMetadata] = ModelMetadata(
        uuid=UUID("a1b2c3d4-0001-4000-8000-000000000001"),
        name="growing_degree_days",
        display_name="Growing Degree Days (GDD)",
        version="2.0.0",
        layer=ModelLayer.WEATHER,
        description="Daily and cumulative GDD accumulation with configurable base temperature.",
        supported_crops=None,
        required_weather_fields=["air_temperature"],
        citation="McMaster & Wilhelm (1997). Agricultural and Forest Meteorology, 87(4), 291-300.",
        author="AgStack Foundation",
    )

    def validate_parameters(self, parameters: dict[str, object] | None) -> dict[str, object]:
        params = dict(parameters) if parameters else {}
        base = params.get("base_temp", _DEFAULT_BASE_TEMP)
        upper = params.get("upper_threshold", _DEFAULT_UPPER_THRESHOLD)
        if not isinstance(base, (int, float)):
            raise ModelValidationError(f"base_temp must be numeric, got {type(base)}")
        if not isinstance(upper, (int, float)):
            raise ModelValidationError(f"upper_threshold must be numeric, got {type(upper)}")
        if float(base) >= float(upper):
            raise ModelValidationError("base_temp must be less than upper_threshold")
        params["base_temp"] = float(base)
        params["upper_threshold"] = float(upper)
        return params

    def calculate(
        self,
        weather_data: WeatherDataFrame,
        parameters: dict[str, object] | None = None,
        threat: ThreatDefinition | None = None,
    ) -> ModelResult:
        params = self.validate_parameters(parameters)
        base_temp = float(params["base_temp"])
        upper_threshold = float(params["upper_threshold"])

        temps = weather_data["air_temperature"]
        ts = weather_data.timestamps

        unique_dates = np.unique(ts.astype("datetime64[D]"))
        daily_scores: list[DailyScore] = []
        cumulative = 0.0

        for day in unique_dates:
            mask = ts.astype("datetime64[D]") == day
            day_temps = temps[mask]

            if len(day_temps) == 0:
                continue

            t_avg = float(np.mean(day_temps))
            t_clamped = min(max(t_avg, base_temp), upper_threshold)
            gdd = max(0.0, t_clamped - base_temp)
            cumulative += gdd

            daily_scores.append(DailyScore(
                date=day.astype("datetime64[D]").astype(object),
                value=round(cumulative, 2),
            ))

        return ModelResult(
            model_uuid=self.metadata.uuid,
            model_name=self.metadata.name,
            computed_at=datetime.now(tz=timezone.utc),
            start_date=daily_scores[0].date if daily_scores else unique_dates[0].astype(object),
            end_date=daily_scores[-1].date if daily_scores else unique_dates[-1].astype(object),
            daily_scores=daily_scores,
            summary={
                "total_gdd": round(cumulative, 2),
                "base_temp": base_temp,
                "upper_threshold": upper_threshold,
                "days": len(daily_scores),
            },
        )
