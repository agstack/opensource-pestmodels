"""Heat Stress Index -- a minimal, self-contained example model.

Counts hours above a crop-specific temperature threshold and turns the daily
tally into a bounded risk score. It exists to show the *shape* of a publishable
model, not to be agronomically authoritative.

A model is pure computation: it receives a WeatherDataFrame and returns a
ModelResult. It does NOT fetch weather, resolve GeoIDs, or talk to the network --
agstack-pnd's runtime does all of that and hands you clean, aligned arrays.
"""

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
    RiskLevel,
    ThreatDefinition,
    WeatherDataFrame,
)

_DEFAULT_THRESHOLD_C = 32.0


class HeatStressIndex(PestModelBase):
    """Daily heat-stress risk from hours above a temperature threshold.

    Give each model a STABLE, UNIQUE uuid (uuid4 once, then never change it) --
    it is the model's identity across the whole DPI. If you rev the science,
    bump ``version``; only mint a new uuid for a genuinely different model.
    """

    metadata: ClassVar[ModelMetadata] = ModelMetadata(
        uuid=UUID("f0000000-1111-4222-8333-444444444444"),
        name="heat_stress_index",
        display_name="Heat Stress Index (example)",
        version="0.1.0",
        layer=ModelLayer.WEATHER,
        description="Counts hours above a threshold temperature and scores daily heat stress.",
        supported_crops=None,
        required_weather_fields=["air_temperature"],
        citation="Example template model -- not for production use.",
        author="Your Lab",
    )

    def validate_parameters(self, parameters: dict[str, object] | None) -> dict[str, object]:
        params = dict(parameters) if parameters else {}
        threshold = params.get("threshold_c", _DEFAULT_THRESHOLD_C)
        if not isinstance(threshold, (int, float)):
            raise ModelValidationError(f"threshold_c must be numeric, got {type(threshold)}")
        params["threshold_c"] = float(threshold)
        return params

    def calculate(
        self,
        weather_data: WeatherDataFrame,
        parameters: dict[str, object] | None = None,
        threat: ThreatDefinition | None = None,
    ) -> ModelResult:
        params = self.validate_parameters(parameters)
        threshold = float(params["threshold_c"])

        temps = weather_data["air_temperature"]
        ts = weather_data.timestamps
        days = ts.astype("datetime64[D]")

        daily_scores: list[DailyScore] = []
        for day in np.unique(days):
            day_temps = temps[days == day]
            if len(day_temps) == 0:
                continue
            hours_over = int(np.sum(day_temps > threshold))
            # 0 hours -> 0.0, >=12 hours -> 1.0 (bounded, monotonic).
            score = min(1.0, hours_over / 12.0)
            daily_scores.append(DailyScore(
                date=day.astype(object),
                value=round(score, 3),
                risk_level=self._risk_level(score),
            ))

        peak = max((s.value for s in daily_scores), default=0.0)
        return ModelResult(
            model_uuid=self.metadata.uuid,
            model_name=self.metadata.name,
            computed_at=datetime.now(tz=timezone.utc),
            start_date=daily_scores[0].date if daily_scores else days[0].astype(object),
            end_date=daily_scores[-1].date if daily_scores else days[-1].astype(object),
            daily_scores=daily_scores,
            summary={"threshold_c": threshold, "peak_risk": peak, "days": len(daily_scores)},
        )

    @staticmethod
    def _risk_level(score: float) -> RiskLevel:
        if score >= 0.75:
            return RiskLevel.CRITICAL
        if score >= 0.5:
            return RiskLevel.HIGH
        if score >= 0.25:
            return RiskLevel.MODERATE
        return RiskLevel.LOW
