"""Unit tests for the example HeatStressIndex model.

Copy this pattern for your own model: build a WeatherDataFrame, call calculate(),
assert on the ModelResult. No network, no fixtures beyond arrays.
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from agstack_pnd.foundation.types import RiskLevel, WeatherDataFrame
from my_pnd_model.heat_stress import HeatStressIndex


def _weather(hourly_temps: list[float], start="2026-07-01T00:00:00") -> WeatherDataFrame:
    base = np.datetime64(datetime.fromisoformat(start).replace(tzinfo=None))
    timestamps = np.array([base + np.timedelta64(h, "h") for h in range(len(hourly_temps))])
    return WeatherDataFrame(
        timestamps=timestamps,
        fields={"air_temperature": np.array(hourly_temps, dtype=np.float64)},
    )


def test_no_heat_stress_scores_zero():
    result = HeatStressIndex().calculate(_weather([20.0] * 24))
    assert result.daily_scores[0].value == 0.0
    assert result.daily_scores[0].risk_level == RiskLevel.LOW


def test_many_hot_hours_score_high():
    temps = [35.0] * 24  # every hour above the 32C default threshold
    result = HeatStressIndex().calculate(_weather(temps))
    assert result.daily_scores[0].value == 1.0
    assert result.daily_scores[0].risk_level == RiskLevel.CRITICAL
    assert result.summary["peak_risk"] == 1.0


def test_threshold_is_configurable():
    temps = [30.0] * 24
    hot = HeatStressIndex().calculate(_weather(temps), parameters={"threshold_c": 25.0})
    cool = HeatStressIndex().calculate(_weather(temps), parameters={"threshold_c": 35.0})
    assert hot.daily_scores[0].value > cool.daily_scores[0].value


def test_model_has_stable_identity():
    md = HeatStressIndex.metadata
    assert str(md.uuid) == "f0000000-1111-4222-8333-444444444444"
    assert md.required_weather_fields == ["air_temperature"]
