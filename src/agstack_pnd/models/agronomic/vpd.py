"""Vapour Pressure Deficit (VPD) calculator with rolling averages.

VPD = (1 - RH/100) * 0.6108 * exp(17.27 * T / (T + 237.3))

Based on the Tetens equation for saturation vapour pressure.
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


def _vpd(temp_c: float, rh: float) -> float:
    """Compute VPD in kPa using Tetens equation."""
    es = 0.6108 * np.exp(17.27 * temp_c / (temp_c + 237.3))
    return float((1.0 - rh / 100.0) * es)


class VapourPressureDeficit(PestModelBase):
    """Daily VPD with optional rolling averages (3d, 7d).

    Reports daily mean VPD in kPa. Summary includes 3-day and 7-day
    rolling averages for the final day.
    """

    metadata: ClassVar[ModelMetadata] = ModelMetadata(
        uuid=UUID("a1b2c3d4-0003-4000-8000-000000000003"),
        name="vpd",
        display_name="Vapour Pressure Deficit (VPD)",
        version="2.0.0",
        layer=ModelLayer.AGRONOMIC,
        description="Daily mean VPD (kPa) from temperature and RH, with rolling averages.",
        supported_crops=None,
        required_weather_fields=["air_temperature", "relative_humidity"],
        citation="Tetens (1930). Zeitschrift für Geophysik, 6, 297-309.",
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
        rh = weather_data["relative_humidity"]
        ts = weather_data.timestamps

        unique_dates = np.unique(ts.astype("datetime64[D]"))
        daily_vpds: list[float] = []
        daily_scores: list[DailyScore] = []

        for day in unique_dates:
            mask = ts.astype("datetime64[D]") == day
            day_temps = temps[mask]
            day_rh = rh[mask]
            vpd_vals = [_vpd(float(t), float(h)) for t, h in zip(day_temps, day_rh)]
            mean_vpd = float(np.mean(vpd_vals)) if vpd_vals else 0.0
            daily_vpds.append(mean_vpd)
            daily_scores.append(DailyScore(
                date=day.astype("datetime64[D]").astype(object),
                value=round(mean_vpd, 4),
            ))

        vpd_3d = float(np.mean(daily_vpds[-3:])) if len(daily_vpds) >= 3 else None
        vpd_7d = float(np.mean(daily_vpds[-7:])) if len(daily_vpds) >= 7 else None

        return ModelResult(
            model_uuid=self.metadata.uuid,
            model_name=self.metadata.name,
            computed_at=datetime.now(tz=timezone.utc),
            start_date=daily_scores[0].date if daily_scores else unique_dates[0].astype(object),
            end_date=daily_scores[-1].date if daily_scores else unique_dates[-1].astype(object),
            daily_scores=daily_scores,
            summary={
                "mean_vpd_kpa": round(float(np.mean(daily_vpds)), 4) if daily_vpds else 0.0,
                "vpd_3d": round(vpd_3d, 4) if vpd_3d is not None else None,
                "vpd_7d": round(vpd_7d, 4) if vpd_7d is not None else None,
                "days": len(daily_scores),
            },
        )
