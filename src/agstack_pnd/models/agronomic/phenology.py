"""Phenological gating -- GDD-fraction windowing with trapezoidal membership."""

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

_PHENO_MARGIN = 0.12  # 12% soft-transition margin


def _trapezoidal_membership(x: float, lo: float, hi: float, margin: float) -> float:
    """Trapezoidal membership function for phenological gating.

    Full membership (1.0) between lo and hi.
    Linear ramp from 0 to 1 in the margin zone below lo and above hi.
    """
    spread = (hi - lo) * margin if hi > lo else margin
    if x < lo - spread:
        return 0.0
    if x < lo:
        return (x - (lo - spread)) / spread if spread > 0 else 1.0
    if x <= hi:
        return 1.0
    if x < hi + spread:
        return 1.0 - (x - hi) / spread if spread > 0 else 0.0
    return 0.0


class PhenologicalGating(PestModelBase):
    """Reports a daily phenological activity score (0-1) based on GDD accumulation.

    Uses trapezoidal membership over a GDD window (absolute or fraction-of-annual).
    The window can come from ThreatDefinition.bio_params or from explicit parameters.
    """

    metadata: ClassVar[ModelMetadata] = ModelMetadata(
        uuid=UUID("a1b2c3d4-0003-4000-8000-000000000005"),
        name="phenology",
        display_name="Phenological Gating",
        version="2.0.0",
        layer=ModelLayer.AGRONOMIC,
        description="Trapezoidal GDD-fraction phenological activity window.",
        supported_crops=None,
        required_weather_fields=["air_temperature"],
        dependencies=["growing_degree_days"],
        citation="OpenAgri PND fuzzy risk system.",
        author="AgStack Foundation",
    )

    def validate_parameters(self, parameters: dict[str, object] | None) -> dict[str, object]:
        params = dict(parameters) if parameters else {}
        base_temp = params.get("base_temp", 5.0)
        if not isinstance(base_temp, (int, float)):
            raise ModelValidationError(f"base_temp must be numeric, got {type(base_temp)}")
        params["base_temp"] = float(base_temp)
        return params

    def calculate(
        self,
        weather_data: WeatherDataFrame,
        parameters: dict[str, object] | None = None,
        threat: ThreatDefinition | None = None,
    ) -> ModelResult:
        params = self.validate_parameters(parameters)
        base_temp = float(params["base_temp"])

        pheno_lo: float | None = params.get("pheno_lo")  # type: ignore[assignment]
        pheno_hi: float | None = params.get("pheno_hi")  # type: ignore[assignment]

        if threat and threat.bio_params:
            bp = threat.bio_params
            if pheno_lo is None:
                pheno_lo = bp.pheno_lo
            if pheno_hi is None:
                pheno_hi = bp.pheno_hi
            if pheno_lo is None and bp.pheno_frac_lo is not None:
                ref = bp.pheno_fraction_ref_gdd5
                pheno_lo = bp.pheno_frac_lo * ref
                pheno_hi = (bp.pheno_frac_hi or 1.0) * ref

        if pheno_lo is None:
            pheno_lo = 100.0
        if pheno_hi is None:
            pheno_hi = 2000.0

        temps = weather_data["air_temperature"]
        ts = weather_data.timestamps
        unique_dates = np.unique(ts.astype("datetime64[D]"))

        cumulative_gdd = 0.0
        daily_scores: list[DailyScore] = []

        for day in unique_dates:
            mask = ts.astype("datetime64[D]") == day
            day_temps = temps[mask]
            t_avg = float(np.mean(day_temps)) if len(day_temps) > 0 else base_temp
            gdd = max(0.0, t_avg - base_temp)
            cumulative_gdd += gdd

            mu = _trapezoidal_membership(cumulative_gdd, pheno_lo, pheno_hi, _PHENO_MARGIN)
            daily_scores.append(DailyScore(
                date=day.astype("datetime64[D]").astype(object),
                value=round(mu, 4),
            ))

        return ModelResult(
            model_uuid=self.metadata.uuid,
            model_name=self.metadata.name,
            computed_at=datetime.now(tz=timezone.utc),
            start_date=daily_scores[0].date if daily_scores else unique_dates[0].astype(object),
            end_date=daily_scores[-1].date if daily_scores else unique_dates[-1].astype(object),
            daily_scores=daily_scores,
            summary={
                "pheno_lo_gdd": pheno_lo,
                "pheno_hi_gdd": pheno_hi,
                "final_cumulative_gdd": round(cumulative_gdd, 2),
                "base_temp": base_temp,
                "days": len(daily_scores),
            },
        )
