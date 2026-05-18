"""Dynamic Chill Portions model.

Citation: Fishman, Erez & Couvillon (1987). The temperature dependence
of dormancy breaking in plants. Journal of Theoretical Biology, 130(3), 307-321.
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

# Model constants
_SLP = 1.6
_TETMLT = 277.0
_A0 = 139500.0
_A1 = 2.567e18
_E0 = 4153.5
_E1 = 12888.8


class ChillPortions(PestModelBase):
    """Dynamic chill portions (Israeli/Fishman model).

    Uses a two-step biochemical model with reversible intermediate and
    irreversible chill portion accumulation. Temperature must be in Celsius.
    """

    metadata: ClassVar[ModelMetadata] = ModelMetadata(
        uuid=UUID("a1b2c3d4-0002-4000-8000-000000000003"),
        name="chill_portions",
        display_name="Chill Portions (Dynamic Model)",
        version="2.0.0",
        layer=ModelLayer.WEATHER,
        description="Dynamic chill portions model with reversible/irreversible accumulation.",
        supported_crops=None,
        required_weather_fields=["air_temperature"],
        citation="Fishman, Erez & Couvillon (1987). J. Theoretical Biology, 130(3), 307-321.",
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

        temps_c = weather_data["air_temperature"]
        ts = weather_data.timestamps

        portions = 0.0
        inter_s = 0.0

        unique_dates = np.unique(ts.astype("datetime64[D]"))
        daily_scores: list[DailyScore] = []

        for day in unique_dates:
            mask = ts.astype("datetime64[D]") == day
            day_temps = temps_c[mask]

            for t_c in day_temps:
                t_k = float(t_c) + 273.15
                ftmprt = _SLP * _TETMLT * (t_k - _TETMLT) / t_k
                sr = np.exp(ftmprt)
                xi = sr / (1.0 + sr)
                xs = _A0 / (1.0 + np.exp(_E0 / t_k))
                ak1 = _A1 * np.exp(-_E1 / t_k)

                inter_e = xs - (xs - inter_s) * np.exp(-ak1)

                if inter_e < 1.0:
                    inter_s = inter_e
                    delt = 0.0
                else:
                    delt = inter_e * xi
                    inter_s = inter_e - delt

                portions += delt

            daily_scores.append(DailyScore(
                date=day.astype("datetime64[D]").astype(object),
                value=round(portions, 4),
            ))

        return ModelResult(
            model_uuid=self.metadata.uuid,
            model_name=self.metadata.name,
            computed_at=datetime.now(tz=timezone.utc),
            start_date=daily_scores[0].date if daily_scores else unique_dates[0].astype(object),
            end_date=daily_scores[-1].date if daily_scores else unique_dates[-1].astype(object),
            daily_scores=daily_scores,
            summary={"total_portions": round(portions, 4), "days": len(daily_scores)},
        )
