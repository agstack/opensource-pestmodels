"""Humidity Streak tracker -- consecutive days at RH thresholds."""

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

_DEFAULT_THRESHOLD = 80.0
_VALID_THRESHOLDS = (60.0, 70.0, 75.0, 80.0, 85.0, 90.0, 95.0)


class HumidityStreak(PestModelBase):
    """Tracks consecutive days where daily max RH exceeds a threshold.

    Default threshold is 80%. Streak resets to 0 on any day below threshold.
    Reports running streak length per day.
    """

    metadata: ClassVar[ModelMetadata] = ModelMetadata(
        uuid=UUID("a1b2c3d4-0003-4000-8000-000000000004"),
        name="humidity_streak",
        display_name="Humidity Streak Tracker",
        version="2.0.0",
        layer=ModelLayer.AGRONOMIC,
        description="Consecutive days where max RH exceeds a configurable threshold.",
        supported_crops=None,
        required_weather_fields=["relative_humidity"],
        author="AgStack Foundation",
    )

    def validate_parameters(self, parameters: dict[str, object] | None) -> dict[str, object]:
        params = dict(parameters) if parameters else {}
        threshold = params.get("rh_threshold", _DEFAULT_THRESHOLD)
        if not isinstance(threshold, (int, float)):
            from agstack_pnd.foundation.exceptions import ModelValidationError

            raise ModelValidationError(f"rh_threshold must be numeric, got {type(threshold)}")
        params["rh_threshold"] = float(threshold)
        return params

    def calculate(
        self,
        weather_data: WeatherDataFrame,
        parameters: dict[str, object] | None = None,
        threat: ThreatDefinition | None = None,
    ) -> ModelResult:
        params = self.validate_parameters(parameters)
        threshold = float(params["rh_threshold"])

        rh = weather_data["relative_humidity"]
        ts = weather_data.timestamps

        unique_dates = np.unique(ts.astype("datetime64[D]"))
        daily_scores: list[DailyScore] = []
        streak = 0
        max_streak = 0

        for day in unique_dates:
            mask = ts.astype("datetime64[D]") == day
            rh_max = float(np.max(rh[mask])) if np.any(mask) else 0.0

            if rh_max >= threshold:
                streak += 1
            else:
                streak = 0

            max_streak = max(max_streak, streak)
            daily_scores.append(DailyScore(
                date=day.astype("datetime64[D]").astype(object),
                value=float(streak),
            ))

        return ModelResult(
            model_uuid=self.metadata.uuid,
            model_name=self.metadata.name,
            computed_at=datetime.now(tz=timezone.utc),
            start_date=daily_scores[0].date if daily_scores else unique_dates[0].astype(object),
            end_date=daily_scores[-1].date if daily_scores else unique_dates[-1].astype(object),
            daily_scores=daily_scores,
            summary={
                "rh_threshold": threshold,
                "max_streak_days": max_streak,
                "final_streak_days": streak,
                "days": len(daily_scores),
            },
        )
