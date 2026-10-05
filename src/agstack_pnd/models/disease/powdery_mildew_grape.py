"""Powdery Mildew (Grape) -- UC IPM model with ascospore and conidial stages.

Citation: UC IPM Pest Management Guidelines: Grape Powdery Mildew.
University of California Agriculture and Natural Resources.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import ClassVar
from uuid import UUID

import numpy as np

from agstack_pnd.foundation.base_model import PestModelBase
from agstack_pnd.foundation.engine_params import EngineParamsBase, PowderyMildewGrapeParams
from agstack_pnd.foundation.types import (
    DailyScore,
    ModelLayer,
    ModelMetadata,
    ModelResult,
    RiskLevel,
    ThreatDefinition,
    WeatherDataFrame,
)
from agstack_pnd.models.agronomic.leaf_wetness_cart import LeafWetnessCART


def _c_to_f(t: float) -> float:
    return t * 1.8 + 32.0


def _classify_ascospore(
    temp_avg_f: float,
    lwd_hours: float,
    params: PowderyMildewGrapeParams,
) -> str:
    """UC IPM ascospore classification: 'safe' or 'treat'."""
    if temp_avg_f < params.ascospore_temp_break_1_f:
        return "safe"
    if temp_avg_f <= params.ascospore_temp_break_2_f:
        return "treat" if lwd_hours >= params.ascospore_wetness_hours_1 else "safe"
    if temp_avg_f <= params.ascospore_temp_break_3_f:
        return "treat" if lwd_hours >= params.ascospore_wetness_hours_2 else "safe"
    if temp_avg_f <= params.ascospore_temp_break_4_f:
        return "treat" if lwd_hours >= params.ascospore_wetness_hours_3 else "safe"
    return "safe"


class PowderyMildewGrape(PestModelBase):
    """UC IPM grape powdery mildew model.

    Two-phase model:
    1. Ascospore stage: daily mean temp (F) + leaf wetness hours -> safe/treat
    2. Conidial stage: running index (0-100) based on 6-hour windows at 70-85F,
       penalized by days with max >= 95F
    """

    metadata: ClassVar[ModelMetadata] = ModelMetadata(
        uuid=UUID("a1b2c3d4-0004-4000-8000-000000000003"),
        name="powdery_mildew_grape",
        display_name="Powdery Mildew - Grape (UC IPM)",
        version="2.0.0",
        layer=ModelLayer.DISEASE,
        description="Ascospore + conidial stage risk model for grape powdery mildew.",
        supported_crops=["grape"],
        required_weather_fields=[
            "air_temperature", "dew_point", "relative_humidity", "wind_speed",
        ],
        dependencies=["growing_degree_days", "leaf_wetness_cart"],
        citation="UC IPM Pest Management Guidelines: Grape (Powdery Mildew).",
        author="AgStack Foundation",
    )

    engine_params_schema: ClassVar[type[EngineParamsBase] | None] = PowderyMildewGrapeParams

    def validate_parameters(self, parameters: dict[str, object] | None) -> dict[str, object]:
        return dict(parameters) if parameters else {}

    def calculate(
        self,
        weather_data: WeatherDataFrame,
        parameters: dict[str, object] | None = None,
        threat: ThreatDefinition | None = None,
    ) -> ModelResult:
        self.validate_parameters(parameters)
        engine_params = PowderyMildewGrapeParams()
        if threat and threat.engine_type == engine_params.engine_type and threat.engine_params:
            engine_params = PowderyMildewGrapeParams.model_validate(threat.engine_params)

        temps = weather_data["air_temperature"]
        ts = weather_data.timestamps
        unique_dates = np.unique(ts.astype("datetime64[D]"))

        # Leaf wetness via CART model
        has_lwd_fields = all(
            f in weather_data for f in ["dew_point", "relative_humidity", "wind_speed"]
        )
        if has_lwd_fields:
            lwd_result = LeafWetnessCART().calculate(weather_data)
            lwd_by_date = {s.date: s.value for s in lwd_result.daily_scores}
        else:
            lwd_by_date = {}

        # Conidial index tracking
        conidial_index = 0.0
        ascospore_treat_days = 0
        daily_scores: list[DailyScore] = []

        for day in unique_dates:
            mask = ts.astype("datetime64[D]") == day
            day_temps_c = temps[mask]
            day_temps_f = np.array([_c_to_f(float(t)) for t in day_temps_c])
            d = day.astype("datetime64[D]").astype(object)

            temp_avg_f = float(np.mean(day_temps_f)) if len(day_temps_f) > 0 else 0.0
            lwd = lwd_by_date.get(d, 0.0)

            # Ascospore classification
            if _classify_ascospore(temp_avg_f, lwd, engine_params) == "treat":
                ascospore_treat_days += 1

            # Conidial index update
            favorable_hours = sum(
                1
                for t in day_temps_f
                if (
                    engine_params.conidial_favorable_temp_min_f
                    <= t
                    <= engine_params.conidial_favorable_temp_max_f
                )
            )
            consecutive_6h = favorable_hours >= 6
            if consecutive_6h:
                conidial_index = min(100.0, conidial_index + engine_params.conidial_index_gain)
            else:
                conidial_index = max(0.0, conidial_index - engine_params.conidial_index_decay)

            # 95F penalty
            if any(t >= engine_params.conidial_heat_penalty_temp_f for t in day_temps_f):
                conidial_index = max(
                    0.0,
                    conidial_index - engine_params.conidial_index_heat_penalty,
                )

            # Risk classification from conidial index
            if conidial_index >= engine_params.risk_high_threshold:
                risk = RiskLevel.HIGH
            elif conidial_index >= engine_params.risk_moderate_threshold:
                risk = RiskLevel.MODERATE
            else:
                risk = RiskLevel.LOW

            daily_scores.append(DailyScore(
                date=d,
                value=round(conidial_index, 1),
                risk_level=risk,
            ))

        return ModelResult(
            model_uuid=self.metadata.uuid,
            model_name=self.metadata.name,
            computed_at=datetime.now(tz=timezone.utc),
            start_date=daily_scores[0].date if daily_scores else unique_dates[0].astype(object),
            end_date=daily_scores[-1].date if daily_scores else unique_dates[-1].astype(object),
            daily_scores=daily_scores,
            summary={
                "final_conidial_index": conidial_index,
                "max_conidial_index": max((s.value for s in daily_scores), default=0.0),
                "days": len(daily_scores),
                "ascospore_treat_days": ascospore_treat_days,
            },
        )
