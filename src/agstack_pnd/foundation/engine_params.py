"""Typed parameter schemas for pluggable model engines."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, model_validator

from agstack_pnd.foundation.types import RiskLevel


class EngineParamsBase(BaseModel):
    """Base class for model-engine-specific parameter schemas."""

    engine_type: str


class FuzzyRuleSpec(BaseModel):
    """Engine-native fuzzy rule representation used in imported JSON."""

    hum_lo: float
    hum_hi: float
    temp_lo: float
    temp_hi: float
    rain_min: float = 0.0
    risk_level: RiskLevel

    @model_validator(mode="after")
    def validate_ranges(self) -> FuzzyRuleSpec:
        if self.hum_lo > self.hum_hi:
            raise ValueError("hum_lo must be less than or equal to hum_hi")
        if self.temp_lo > self.temp_hi:
            raise ValueError("temp_lo must be less than or equal to temp_hi")
        if self.rain_min < 0:
            raise ValueError("rain_min must be non-negative")
        return self


class FuzzyMamdaniParams(EngineParamsBase):
    """Typed parameter schema for the fuzzy Mamdani risk engine."""

    engine_type: Literal["fuzzy_mamdani"] = "fuzzy_mamdani"
    fuzzy_rules: list[FuzzyRuleSpec] = Field(default_factory=list)


class PowderyMildewGrapeParams(EngineParamsBase):
    """Typed parameter schema for the UC IPM grape powdery mildew model."""

    engine_type: Literal["powdery_mildew_grape"] = "powdery_mildew_grape"
    ascospore_temp_break_1_f: float = 50.0
    ascospore_temp_break_2_f: float = 60.0
    ascospore_temp_break_3_f: float = 70.0
    ascospore_temp_break_4_f: float = 80.0
    ascospore_wetness_hours_1: float = 6.0
    ascospore_wetness_hours_2: float = 4.0
    ascospore_wetness_hours_3: float = 3.0
    conidial_favorable_temp_min_f: float = 70.0
    conidial_favorable_temp_max_f: float = 85.0
    conidial_heat_penalty_temp_f: float = 95.0
    conidial_index_gain: float = 20.0
    conidial_index_decay: float = 10.0
    conidial_index_heat_penalty: float = 10.0
    risk_high_threshold: float = 60.0
    risk_moderate_threshold: float = 30.0

    @model_validator(mode="after")
    def validate_thresholds(self) -> PowderyMildewGrapeParams:
        if not (
            self.ascospore_temp_break_1_f
            < self.ascospore_temp_break_2_f
            < self.ascospore_temp_break_3_f
            < self.ascospore_temp_break_4_f
        ):
            raise ValueError("ascospore temperature breaks must be strictly increasing")
        if not (
            self.ascospore_wetness_hours_1
            >= self.ascospore_wetness_hours_2
            >= self.ascospore_wetness_hours_3
        ):
            raise ValueError("ascospore wetness thresholds must be non-increasing")
        if self.conidial_favorable_temp_min_f > self.conidial_favorable_temp_max_f:
            raise ValueError("favorable temperature minimum must not exceed the maximum")
        if self.risk_moderate_threshold > self.risk_high_threshold:
            raise ValueError("moderate risk threshold must not exceed high risk threshold")
        if min(
            self.conidial_index_gain,
            self.conidial_index_decay,
            self.conidial_index_heat_penalty,
        ) < 0:
            raise ValueError("conidial index adjustments must be non-negative")
        return self


class GDDFlightParams(EngineParamsBase):
    """Typed parameter schema for GDD-based insect flight models."""
    ...

    @model_validator(mode="after")
    def validate_gdd_ordering(self) -> GDDFlightParams:
        return self

class NeuralNetParams(EngineParamsBase):
    """Typed parameter schema for externally trained neural-network models."""
    ...

    @model_validator(mode="after")
    def validate_neural_net(self) -> NeuralNetParams:
        return self


ModelEngineParams = Annotated[
    FuzzyMamdaniParams | GDDFlightParams | NeuralNetParams | PowderyMildewGrapeParams,
    Field(discriminator="engine_type"),
]


def build_legacy_fuzzy_engine_params(
    *,
    fuzzy_rules: list[dict[str, Any]] | None,
) -> FuzzyMamdaniParams:
    """Build the new fuzzy-engine schema from the legacy threat layout."""

    return FuzzyMamdaniParams(
        fuzzy_rules=[
            FuzzyRuleSpec.model_validate(rule)
            for rule in fuzzy_rules or []
        ],
    )