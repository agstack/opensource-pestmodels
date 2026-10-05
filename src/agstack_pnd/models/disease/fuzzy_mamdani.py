"""Fuzzy Mamdani risk engine.

Core engine: trapezoidal membership functions for temperature, humidity,
and rainfall, AND-aggregation (min), weighted defuzzification, and
post-processing gates (streak penalty, Mills-type wetness gate,
phenological scaling, lethal temperature cutoff).

Ported from the OpenAgri-EU fork of PestAndDiseaseManagement.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import ClassVar
from uuid import UUID

import numpy as np

from agstack_pnd.foundation.base_model import PestModelBase
from agstack_pnd.foundation.engine_params import EngineParamsBase, FuzzyMamdaniParams
from agstack_pnd.foundation.exceptions import ModelValidationError
from agstack_pnd.foundation.types import (
    BioParams,
    DailyScore,
    FuzzyRule,
    ModelLayer,
    ModelMetadata,
    ModelResult,
    RiskLevel,
    ThreatDefinition,
    WeatherDataFrame,
)
from agstack_pnd.models.agronomic.humidity_streak import HumidityStreak
from agstack_pnd.models.agronomic.leaf_wetness_rh import LeafWetnessRH
from agstack_pnd.models.agronomic.phenology import PhenologicalGating
from agstack_pnd.models.weather.growing_degree_days import GrowingDegreeDays

_RISK_SCORES = {
    RiskLevel.LOW: 10.0,
    RiskLevel.MODERATE: 40.0,
    RiskLevel.HIGH: 80.0,
    RiskLevel.CRITICAL: 100.0,
}

_RISK_THRESHOLDS = [
    (88.0, RiskLevel.CRITICAL),
    (65.0, RiskLevel.HIGH),
    (30.0, RiskLevel.MODERATE),
    (0.0, RiskLevel.LOW),
]

_TRANSITION_FRAC = 0.15

# Fungal/bacterial genera that get 7-day moving average smoothing
_PATHOGEN_GENERA = frozenset([
    "venturia", "plasmopora", "plasmopara", "uncinula", "erysiphe",
    "botrytis", "monilia", "monilinia", "taphrina", "erwinia",
    "guignardia", "phomopsis", "colletotrichum", "pseudomonas",
    "pseudocercospora", "alternaria", "hemileia", "phytophthora",
    "moniliophthora", "oidium",
])


def _trapezoid(x: float, lo: float, hi: float) -> float:
    """Trapezoidal membership with 15% transition zones."""
    spread = (hi - lo) * _TRANSITION_FRAC if hi > lo else 1.0
    if x < lo - spread:
        return 0.0
    if x < lo:
        return (x - (lo - spread)) / spread if spread > 0 else 1.0
    if x <= hi:
        return 1.0
    if x < hi + spread:
        return 1.0 - (x - hi) / spread if spread > 0 else 0.0
    return 0.0


def _is_pathogen(scientific_name: str) -> bool:
    name_lower = scientific_name.lower()
    return any(g in name_lower for g in _PATHOGEN_GENERA)


def _classify_risk(score: float) -> RiskLevel:
    for threshold, level in _RISK_THRESHOLDS:
        if score >= threshold:
            return level
    return RiskLevel.LOW


class FuzzyMamdaniRisk(PestModelBase):
    """Fuzzy Mamdani pest/disease risk engine.

    A single model class that operates on ANY of the 54 crop-threat pairings
    based on the ThreatDefinition passed in. The threat definition provides:
    - fuzzy_rules: humidity/temp/rainfall ranges per risk level
    - bio_params: lethal temps, optimal temps, streak requirements, phenology windows

    The engine:
    1. Computes daily features (avg temp, max RH, cumulative rainfall)
    2. Applies 7-day moving average for pathogen genera (fungi/bacteria)
    3. Fuzzifies each rule via trapezoidal membership
    4. AND-aggregates: mu = min(mu_temp, mu_humidity, mu_rainfall)
    5. Weighted defuzzification: score = sum(mu_i * risk_i) / sum(mu_i)
    6. Post-processing: lethal temp cutoff, streak penalty, wetness gate, phenology scaling
    """

    metadata: ClassVar[ModelMetadata] = ModelMetadata(
        uuid=UUID("a1b2c3d4-0004-4000-8000-000000000001"),
        name="fuzzy_mamdani_risk",
        display_name="Fuzzy Mamdani Risk Engine",
        version="2.0.0",
        layer=ModelLayer.DISEASE,
        description=(
            "Mamdani fuzzy inference for pest/disease risk. Operates on any "
            "crop-threat pairing via ThreatDefinition parameter."
        ),
        supported_crops=None,  # works with any crop via ThreatDefinition
        required_weather_fields=[
            "air_temperature", "relative_humidity", "precipitation",
        ],
        dependencies=[
            "growing_degree_days", "leaf_wetness_rh",
            "humidity_streak", "phenology",
        ],
        citation="OpenAgri-EU PND fuzzy risk system; Agrobit S.r.l.",
        author="AgStack Foundation / OpenAgri",
    )

    engine_params_schema: ClassVar[type[EngineParamsBase] | None] = FuzzyMamdaniParams

    def validate_parameters(self, parameters: dict[str, object] | None) -> dict[str, object]:
        return dict(parameters) if parameters else {}

    def calculate(
        self,
        weather_data: WeatherDataFrame,
        parameters: dict[str, object] | None = None,
        threat: ThreatDefinition | None = None,
    ) -> ModelResult:
        if threat is None:
            raise ModelValidationError(
                "FuzzyMamdaniRisk requires a ThreatDefinition (crop-threat pairing)"
            )
        if not threat.fuzzy_rules:
            raise ModelValidationError(
                f"No fuzzy rules defined for {threat.common_name} on {threat.crop}"
            )

        self.validate_parameters(parameters)
        bp = threat.bio_params
        use_ma = _is_pathogen(threat.scientific_name)

        temps = weather_data["air_temperature"]
        rh = weather_data["relative_humidity"]
        precip = weather_data["precipitation"]
        ts = weather_data.timestamps

        unique_dates = np.unique(ts.astype("datetime64[D]"))
        n_days = len(unique_dates)

        daily_temp_avg = np.zeros(n_days)
        daily_rh_max = np.zeros(n_days)
        daily_rain = np.zeros(n_days)

        for i, day in enumerate(unique_dates):
            mask = ts.astype("datetime64[D]") == day
            daily_temp_avg[i] = float(np.mean(temps[mask])) if np.any(mask) else 0.0
            daily_rh_max[i] = float(np.max(rh[mask])) if np.any(mask) else 0.0
            daily_rain[i] = float(np.sum(precip[mask]))

        # 7-day moving average for pathogen genera
        if use_ma and n_days >= 7:
            kernel = np.ones(7) / 7.0
            temp_smooth = np.convolve(daily_temp_avg, kernel, mode="same")
            rh_smooth = np.convolve(daily_rh_max, kernel, mode="same")
        else:
            temp_smooth = daily_temp_avg
            rh_smooth = daily_rh_max

        # 3-day cumulative rainfall
        rain_3d = np.zeros(n_days)
        for i in range(n_days):
            start = max(0, i - 2)
            rain_3d[i] = float(np.sum(daily_rain[start : i + 1]))

        # Leaf wetness + humidity streak + phenology (via sub-models)
        lw_result = LeafWetnessRH().calculate(weather_data)
        streak_result = HumidityStreak().calculate(
            weather_data, {"rh_threshold": 80.0}
        )
        pheno_result = PhenologicalGating().calculate(
            weather_data,
            {"base_temp": bp.t_base},
            threat=threat,
        )

        lw_by_date = {s.date: s.value for s in lw_result.daily_scores}
        streak_by_date = {s.date: s.value for s in streak_result.daily_scores}
        pheno_by_date = {s.date: s.value for s in pheno_result.daily_scores}

        daily_scores: list[DailyScore] = []

        for i, day in enumerate(unique_dates):
            d = day.astype("datetime64[D]").astype(object)
            t = float(temp_smooth[i])
            h = float(rh_smooth[i])
            r = float(rain_3d[i])

            # Lethal temperature gate
            if t < bp.t_lethal_min or t > bp.t_lethal_max:
                daily_scores.append(DailyScore(date=d, value=0.0, risk_level=RiskLevel.LOW))
                continue

            # Fuzzy inference
            weighted_sum = 0.0
            weight_total = 0.0

            for rule in threat.fuzzy_rules:
                mu_temp = _trapezoid(t, rule.temp_lo, rule.temp_hi)
                mu_hum = _trapezoid(h, rule.hum_lo, rule.hum_hi)
                mu_rain = 1.0 if r >= rule.rain_min else _trapezoid(r, rule.rain_min * 0.5, rule.rain_min)
                mu = min(mu_temp, mu_hum, mu_rain)

                if mu > 0:
                    score = _RISK_SCORES[rule.risk_level]
                    weighted_sum += mu * score
                    weight_total += mu

            raw_score = weighted_sum / weight_total if weight_total > 0 else 0.0

            # Streak penalty
            streak_days = streak_by_date.get(d, 0.0)
            if streak_days < bp.min_streak:
                penalty = max(0.30, streak_days / bp.min_streak)
                raw_score *= penalty

            # Wetness gate
            wetness = lw_by_date.get(d, 0.0)
            if raw_score >= 88.0 and wetness < bp.min_wetness_hours_critical:
                raw_score = min(raw_score, 87.0)
            if raw_score >= 65.0 and wetness < bp.min_wetness_hours_high:
                raw_score = min(raw_score, 64.0)

            # Phenological scaling
            pheno_mu = pheno_by_date.get(d, 1.0)
            raw_score *= pheno_mu

            score = max(0.0, min(100.0, raw_score))
            daily_scores.append(DailyScore(
                date=d,
                value=round(score, 2),
                risk_level=_classify_risk(score),
            ))

        return ModelResult(
            model_uuid=self.metadata.uuid,
            model_name=self.metadata.name,
            computed_at=datetime.now(tz=timezone.utc),
            start_date=daily_scores[0].date if daily_scores else unique_dates[0].astype(object),
            end_date=daily_scores[-1].date if daily_scores else unique_dates[-1].astype(object),
            daily_scores=daily_scores,
            summary={
                "threat": threat.common_name,
                "crop": threat.crop,
                "scientific_name": threat.scientific_name,
                "max_score": max((s.value for s in daily_scores), default=0.0),
                "days_critical": sum(1 for s in daily_scores if s.risk_level == RiskLevel.CRITICAL),
                "days_high": sum(1 for s in daily_scores if s.risk_level == RiskLevel.HIGH),
                "days_moderate": sum(1 for s in daily_scores if s.risk_level == RiskLevel.MODERATE),
                "days_low": sum(1 for s in daily_scores if s.risk_level == RiskLevel.LOW),
                "pathogen_smoothing": use_ma,
            },
        )
