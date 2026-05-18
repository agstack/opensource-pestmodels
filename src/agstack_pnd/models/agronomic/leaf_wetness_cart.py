"""CART/SLD leaf wetness duration classifier.

Hourly classification using air temperature, dew point, relative humidity,
and wind speed to determine wet vs dry leaf surface.

Citation: Kim, Gleason, Jiang, et al. (2002). Predicting leaf wetness duration
using a fuzzy logic/CART system. APS Plant Disease, 86(2), 129-135.
"""

from __future__ import annotations

import math
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


def _classify_hour(
    air_temp: float,
    dew_point: float,
    rel_humidity: float,
    wind_speed_kmh: float,
) -> int:
    """Classify a single hour as wet (1) or dry (0).

    Wind converted from km/h to m/s internally.
    """
    wind_ms = wind_speed_kmh / 3.6
    dpd = air_temp - dew_point  # dew-point depression

    if dpd < 3.7:
        return 1
    if rel_humidity >= 87.8:
        if wind_ms <= 2.5:
            return 1
        if dpd <= 5.3:
            return 1
    if rel_humidity > 73.0 and wind_ms < 2.5:
        threshold = 2.0 * math.sqrt(dpd) + 0.2 * wind_ms ** 0.5
        if dpd <= threshold:
            return 1
    return 0


class LeafWetnessCART(PestModelBase):
    """CART/SLD leaf wetness duration model.

    Classifies each hour as wet or dry, then reports total wet hours per day.
    """

    metadata: ClassVar[ModelMetadata] = ModelMetadata(
        uuid=UUID("a1b2c3d4-0003-4000-8000-000000000001"),
        name="leaf_wetness_cart",
        display_name="Leaf Wetness Duration (CART/SLD)",
        version="2.0.0",
        layer=ModelLayer.AGRONOMIC,
        description="Hourly wet/dry classification using CART decision tree on dew-point depression, RH, and wind.",
        supported_crops=None,
        required_weather_fields=["air_temperature", "dew_point", "relative_humidity", "wind_speed"],
        citation="Kim, Gleason, Jiang et al. (2002). APS Plant Disease, 86(2), 129-135.",
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

        temps = weather_data["air_temperature"]
        dew = weather_data["dew_point"]
        rh = weather_data["relative_humidity"]
        wind = weather_data["wind_speed"]
        ts = weather_data.timestamps

        unique_dates = np.unique(ts.astype("datetime64[D]"))
        daily_scores: list[DailyScore] = []

        for day in unique_dates:
            mask = ts.astype("datetime64[D]") == day
            wet_hours = sum(
                _classify_hour(float(temps[i]), float(dew[i]), float(rh[i]), float(wind[i]))
                for i in np.where(mask)[0]
            )
            daily_scores.append(DailyScore(
                date=day.astype("datetime64[D]").astype(object),
                value=float(wet_hours),
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
