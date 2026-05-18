"""Tests for the Fuzzy Mamdani risk engine."""

import pytest

from agstack_pnd.catalog.loader import get_threat
from agstack_pnd.foundation.exceptions import ModelValidationError
from agstack_pnd.foundation.types import RiskLevel
from agstack_pnd.models.disease.fuzzy_mamdani import FuzzyMamdaniRisk


class TestFuzzyMamdani:
    def test_requires_threat(self, seven_day_weather):
        model = FuzzyMamdaniRisk()
        with pytest.raises(ModelValidationError, match="requires a ThreatDefinition"):
            model.calculate(seven_day_weather)

    def test_grape_downy_mildew(self, seven_day_weather):
        model = FuzzyMamdaniRisk()
        threat = get_threat("grape", "Plasmopora viticola")
        result = model.calculate(seven_day_weather, threat=threat)
        assert len(result.daily_scores) == 7
        assert result.summary["crop"] == "grape"
        for s in result.daily_scores:
            assert 0 <= s.value <= 100
            assert s.risk_level in list(RiskLevel)

    def test_coffee_leaf_rust(self, seven_day_weather):
        model = FuzzyMamdaniRisk()
        threat = get_threat("coffee", "Hemileia vastatrix")
        result = model.calculate(seven_day_weather, threat=threat)
        assert len(result.daily_scores) == 7
        assert result.summary["pathogen_smoothing"] is True
