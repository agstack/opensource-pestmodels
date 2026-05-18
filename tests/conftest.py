"""Shared test fixtures -- synthetic weather data for reproducible model testing."""

from __future__ import annotations

from datetime import date

import numpy as np
import pytest

from agstack_pnd.foundation.types import WeatherDataFrame


@pytest.fixture
def seven_day_weather() -> WeatherDataFrame:
    """7 days of hourly synthetic weather data (168 hours).

    Simulates a warm, humid period suitable for testing disease models.
    """
    n_hours = 7 * 24
    base = np.datetime64("2026-05-01T00:00")
    timestamps = np.array([base + np.timedelta64(h, "h") for h in range(n_hours)])

    hours_of_day = np.array([h % 24 for h in range(n_hours)])
    temp = 18.0 + 7.0 * np.sin(np.pi * (hours_of_day - 6) / 12.0)
    rh = 75.0 + 15.0 * np.cos(np.pi * (hours_of_day - 6) / 12.0)
    rh = np.clip(rh, 40.0, 100.0)
    dew_point = temp - (100.0 - rh) / 5.0
    wind_speed = 5.0 + 3.0 * np.sin(np.pi * hours_of_day / 24.0)
    precip = np.zeros(n_hours)
    for d in [1, 3, 5]:
        precip[d * 24 + 10 : d * 24 + 14] = 2.0

    return WeatherDataFrame(
        timestamps=timestamps,
        fields={
            "air_temperature": temp,
            "relative_humidity": rh,
            "dew_point": dew_point,
            "wind_speed": wind_speed,
            "precipitation": precip,
        },
    )


@pytest.fixture
def thirty_day_weather() -> WeatherDataFrame:
    """30 days of hourly synthetic weather for longer-range model tests."""
    n_hours = 30 * 24
    base = np.datetime64("2026-03-01T00:00")
    timestamps = np.array([base + np.timedelta64(h, "h") for h in range(n_hours)])

    hours_of_day = np.array([h % 24 for h in range(n_hours)])
    day_index = np.array([h // 24 for h in range(n_hours)])
    seasonal = 5.0 + day_index * 0.3
    temp = seasonal + 6.0 * np.sin(np.pi * (hours_of_day - 6) / 12.0)
    rh = 70.0 + 10.0 * np.cos(np.pi * (hours_of_day - 6) / 12.0)
    rh = np.clip(rh, 35.0, 100.0)
    dew_point = temp - (100.0 - rh) / 5.0
    wind_speed = 4.0 + 2.0 * np.random.default_rng(42).random(n_hours)
    precip = np.zeros(n_hours)
    for d in range(0, 30, 4):
        precip[d * 24 + 8 : d * 24 + 12] = 1.5

    return WeatherDataFrame(
        timestamps=timestamps,
        fields={
            "air_temperature": temp,
            "relative_humidity": rh,
            "dew_point": dew_point,
            "wind_speed": wind_speed,
            "precipitation": precip,
        },
    )
