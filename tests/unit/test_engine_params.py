"""Tests for typed engine-param schemas and open registry lookup."""

import pytest

from agstack_pnd.foundation.engine_params import (
    FuzzyMamdaniParams,
    GDDFlightParams,
    NeuralNetParams,
    PowderyMildewGrapeParams,
)
from agstack_pnd.foundation.exceptions import EngineTypeNotFound
from agstack_pnd.foundation.model_registry import ModelRegistry


class TestFuzzyMamdaniParams:
    def test_accepts_fuzzy_rules(self):
        params = FuzzyMamdaniParams(fuzzy_rules=[{
            "hum_lo": 90,
            "hum_hi": 100,
            "temp_lo": 15,
            "temp_hi": 24,
            "risk_level": "high",
        }])
        assert params.engine_type == "fuzzy_mamdani"
        assert len(params.fuzzy_rules) == 1


class TestPowderyMildewGrapeParams:
    def test_defaults_match_model_thresholds(self):
        params = PowderyMildewGrapeParams()
        assert params.ascospore_temp_break_1_f == 50.0
        assert params.conidial_favorable_temp_min_f == 70.0
        assert params.conidial_heat_penalty_temp_f == 95.0
        assert params.risk_high_threshold == 60.0

    def test_rejects_unordered_ascospore_breaks(self):
        with pytest.raises(ValueError, match="temperature breaks"):
            PowderyMildewGrapeParams(
                ascospore_temp_break_2_f=45.0,
            )



class TestEngineParamsRegistry:
    def test_resolves_schema_for_registered_model(self):
        registry = ModelRegistry()
        schema = registry.get_engine_params_schema("fuzzy_mamdani")
        assert schema is FuzzyMamdaniParams

    def test_unknown_engine_type_raises(self):
        registry = ModelRegistry()
        with pytest.raises(EngineTypeNotFound):
            registry.get_engine_params_schema("does_not_exist")
