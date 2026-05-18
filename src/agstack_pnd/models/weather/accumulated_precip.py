"""Accumulated Precipitation -- rolling cumulative rainfall."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import ClassVar
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

_VALID_WINDOWS = (3, 7, 10, 14)


class AccumulatedPrecipitation(PestModelBase):
    """Rolling cumulative precipitation over a configurable window.

    Supports 3, 7, 10, or 14-day windows. Reports daily rolling totals.
    """

    metadata: ClassVar[ModelMetadata] = ModelMetadata(
        uuid=UUID("a1b2c3d4-0001-4000-8000-000000000002"),
        name="accumulated_precipitation",
        display_name="Accumulated Precipitation",
        version="2.0.0",
        layer=ModelLayer.WEATHER,
        description="Rolling cumulative rainfall over 3/7/10/14-day windows.",
        supported_crops=None,
        required_weather_fields=["precipitation"],
        author="AgStack Foundation",
    )

    def validate_parameters(self, parameters: dict[str, object] | None) -> dict[str, object]:
        params = dict(parameters) if parameters else {}
        window = params.get("window_days", 7)
        if not isinstance(window, int) or window not in _VALID_WINDOWS:
            raise ModelValidationError(
                f"window_days must be one of {_VALID_WINDOWS}, got {window}"
            )
        params["window_days"] = window
        return params

    def calculate(
        self,
        weather_data: WeatherDataFrame,
        parameters: dict[str, object] | None = None,
        threat: ThreatDefinition | None = None,
    ) -> ModelResult:
        params = self.validate_parameters(parameters)
        window = int(params["window_days"])

        precip = weather_data["precipitation"]
        ts = weather_data.timestamps

        unique_dates = np.unique(ts.astype("datetime64[D]"))
        daily_totals: list[float] = []

        for day in unique_dates:
            mask = ts.astype("datetime64[D]") == day
            daily_totals.append(float(np.sum(precip[mask])))

        daily_scores: list[DailyScore] = []
        for i, day in enumerate(unique_dates):
            start_idx = max(0, i - window + 1)
            rolling = sum(daily_totals[start_idx : i + 1])
            daily_scores.append(DailyScore(
                date=day.astype("datetime64[D]").astype(object),
                value=round(rolling, 2),
            ))

        return ModelResult(
            model_uuid=self.metadata.uuid,
            model_name=self.metadata.name,
            computed_at=datetime.now(tz=timezone.utc),
            start_date=daily_scores[0].date if daily_scores else unique_dates[0].astype(object),
            end_date=daily_scores[-1].date if daily_scores else unique_dates[-1].astype(object),
            daily_scores=daily_scores,
            summary={
                "window_days": window,
                "total_precipitation_mm": round(sum(daily_totals), 2),
                "days": len(daily_scores),
            },
        )
