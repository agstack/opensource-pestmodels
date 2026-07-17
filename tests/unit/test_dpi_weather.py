"""BiteWeatherProvider: parse Pancake weather BITE bodies into WeatherDataFrames."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from agstack_pnd.foundation.exceptions import WeatherFieldNotSupported
from agstack_pnd.providers.dpi_weather import BiteWeatherProvider


def _weather_body(start: date, days: int) -> dict:
    """Build a minimal hourly weather SIRUP body like the Pancake adapters emit."""
    timestamps: list[str] = []
    series: dict[str, list[float]] = {
        "air_temperature": [], "relative_humidity": [], "precipitation": [],
        "wind_speed": [], "dew_point": [],
    }
    daily = []
    for d in range(days):
        day = start + timedelta(days=d)
        daily.append({"date": day.isoformat(), "t_min": 12.0, "t_max": 24.0,
                      "precip": 2.0, "rh_mean": 75.0, "wind": 2.0})
        for h in range(24):
            ts = datetime(day.year, day.month, day.day, h, tzinfo=UTC)
            timestamps.append(ts.isoformat())
            series["air_temperature"].append(12.0 + 12.0 * (h / 23.0))
            series["relative_humidity"].append(75.0)
            series["precipitation"].append(0.1)
            series["wind_speed"].append(2.0)
            series["dew_point"].append(10.0)
    return {"timestamps": timestamps, "series": series, "daily": daily,
            "resolution": "hourly-synthesized-from-daily"}


def _provider_with_body(body: dict) -> BiteWeatherProvider:
    provider = BiteWeatherProvider(geo_id="geo-abc", pancake_url="http://pancake.test")

    async def _fake_resolve():
        return body

    provider._resolve_body = _fake_resolve  # type: ignore[method-assign]
    return provider


@pytest.mark.asyncio
async def test_hourly_series_parsed_and_aligned():
    start = date(2026, 7, 1)
    provider = _provider_with_body(_weather_body(start, days=3))
    wdf = await provider.get_hourly_data(
        0.0, 0.0, start, start + timedelta(days=2),
        ["air_temperature", "relative_humidity", "precipitation"],
    )
    assert wdf.length == 3 * 24
    assert "air_temperature" in wdf
    assert len(wdf["relative_humidity"]) == wdf.length


@pytest.mark.asyncio
async def test_daily_derived_min_max():
    start = date(2026, 7, 1)
    provider = _provider_with_body(_weather_body(start, days=2))
    wdf = await provider.get_hourly_data(
        0.0, 0.0, start, start + timedelta(days=1),
        ["air_temperature_min", "air_temperature_max"],
    )
    assert float(wdf["air_temperature_min"][0]) == 12.0
    assert float(wdf["air_temperature_max"][0]) == 24.0


@pytest.mark.asyncio
async def test_unsupported_field_raises():
    provider = _provider_with_body(_weather_body(date(2026, 7, 1), days=1))
    with pytest.raises(WeatherFieldNotSupported):
        await provider.get_hourly_data(
            0.0, 0.0, date(2026, 7, 1), date(2026, 7, 1), ["solar_radiation"]
        )


@pytest.mark.asyncio
async def test_date_window_filters_hours():
    start = date(2026, 7, 1)
    provider = _provider_with_body(_weather_body(start, days=5))
    # Ask for the middle 2 days only.
    wdf = await provider.get_hourly_data(
        0.0, 0.0, date(2026, 7, 2), date(2026, 7, 3), ["air_temperature"]
    )
    assert wdf.length == 2 * 24


def test_requires_geo_id():
    from agstack_pnd.foundation.exceptions import WeatherProviderError

    with pytest.raises(WeatherProviderError):
        BiteWeatherProvider(geo_id="", pancake_url="http://x")
