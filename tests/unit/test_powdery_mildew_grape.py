"""Tests for the grape powdery mildew model's typed engine parameters."""

from agstack_pnd.foundation.types import BioParams, ThreatDefinition, ThreatType
from agstack_pnd.models.disease.powdery_mildew_grape import PowderyMildewGrape


def test_default_engine_params_match_legacy_behavior(seven_day_weather):
    model = PowderyMildewGrape()
    default_result = model.calculate(seven_day_weather)

    explicit_defaults = ThreatDefinition(
        scientific_name="Erysiphe necator",
        common_name="Powdery mildew",
        threat_type=ThreatType.FUNGUS,
        crop="grape",
        bio_params=BioParams(),
        engine_type="powdery_mildew_grape",
        engine_params={},
    )
    explicit_result = model.calculate(seven_day_weather, threat=explicit_defaults)

    assert explicit_result.daily_scores == default_result.daily_scores


def test_engine_params_override_conidial_index_gain(seven_day_weather):
    model = PowderyMildewGrape()
    default_result = model.calculate(seven_day_weather)
    overridden_threat = ThreatDefinition(
        scientific_name="Erysiphe necator",
        common_name="Powdery mildew",
        threat_type=ThreatType.FUNGUS,
        crop="grape",
        bio_params=BioParams(),
        engine_type="powdery_mildew_grape",
        engine_params={"conidial_index_gain": 5.0},
    )

    overridden_result = model.calculate(seven_day_weather, threat=overridden_threat)

    assert overridden_result.summary["final_conidial_index"] < default_result.summary[
        "final_conidial_index"
    ]