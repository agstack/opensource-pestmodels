"""NOAA Climate Data Online weather provider.

Maps standardized agstack-pnd field names to NOAA CDO API datatypes.
Requires a free NOAA CDO API token: https://www.ncdc.noaa.gov/cdo-web/token

This is the sole shipped weather provider. Community providers can be
added by subclassing WeatherProvider.
"""

from __future__ import annotations

from datetime import date

import httpx
import numpy as np

from agstack_pnd.foundation.exceptions import (
    WeatherFieldNotSupported,
    WeatherProviderError,
)
from agstack_pnd.foundation.types import STANDARD_WEATHER_FIELDS, WeatherDataFrame
from agstack_pnd.foundation.weather_provider import WeatherProvider

NOAA_CDO_BASE = "https://www.ncei.noaa.gov/cdo-web/api/v2"

# Mapping: standardized name -> NOAA CDO datatype ID
_FIELD_MAP: dict[str, str] = {
    "air_temperature": "TAVG",
    "air_temperature_min": "TMIN",
    "air_temperature_max": "TMAX",
    "precipitation": "PRCP",
    "wind_speed": "AWND",
}

_NOAA_SUPPORTED = list(_FIELD_MAP.keys())


class NOAAProvider(WeatherProvider):
    """NOAA Climate Data Online provider.

    Fetches daily weather data from NOAA CDO API v2. Hourly data is
    synthesized from daily min/max via sinusoidal interpolation when
    hourly endpoint is unavailable for the station.
    """

    def __init__(self, api_token: str) -> None:
        if not api_token:
            raise WeatherProviderError("NOAA API token is required")
        self._token = api_token
        self._base_url = NOAA_CDO_BASE

    def provider_name(self) -> str:
        return "NOAA Climate Data Online"

    def supported_fields(self) -> list[str]:
        return list(_NOAA_SUPPORTED)

    async def get_daily_data(
        self,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
        fields: list[str],
    ) -> WeatherDataFrame:
        for f in fields:
            if f not in _FIELD_MAP:
                raise WeatherFieldNotSupported(f, self.provider_name())

        datatypes = ",".join(_FIELD_MAP[f] for f in fields)

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.get(
                    f"{self._base_url}/data",
                    params={
                        "datasetid": "GHCND",
                        "datatypeid": datatypes,
                        "startdate": start_date.isoformat(),
                        "enddate": end_date.isoformat(),
                        "units": "metric",
                        "limit": 1000,
                        "extent": f"{latitude - 0.5},{longitude - 0.5},{latitude + 0.5},{longitude + 0.5}",
                    },
                    headers={"token": self._token},
                )
            except httpx.HTTPError as exc:
                raise WeatherProviderError(f"NOAA API request failed: {exc}") from exc

            if resp.status_code != 200:
                raise WeatherProviderError(
                    f"NOAA API returned {resp.status_code}: {resp.text}"
                )

            data = resp.json()
            results = data.get("results", [])

        if not results:
            raise WeatherProviderError(
                f"No NOAA data for ({latitude}, {longitude}) "
                f"from {start_date} to {end_date}"
            )

        # Group by date
        reverse_map = {v: k for k, v in _FIELD_MAP.items()}
        date_values: dict[str, dict[str, float]] = {}

        for record in results:
            dt = record["date"][:10]
            datatype = record["datatype"]
            std_field = reverse_map.get(datatype)
            if std_field and std_field in fields:
                date_values.setdefault(dt, {})[std_field] = record["value"]

        sorted_dates = sorted(date_values.keys())
        timestamps = np.array(
            [np.datetime64(d) for d in sorted_dates], dtype="datetime64[D]"
        )

        field_arrays: dict[str, np.ndarray] = {}
        for f in fields:
            field_arrays[f] = np.array(
                [date_values.get(d, {}).get(f, np.nan) for d in sorted_dates],
                dtype=np.float64,
            )

        return WeatherDataFrame(timestamps=timestamps, fields=field_arrays)

    async def get_hourly_data(
        self,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
        fields: list[str],
    ) -> WeatherDataFrame:
        """Synthesize hourly data from daily min/max using sinusoidal interpolation."""
        daily_fields = []
        for f in fields:
            if f == "air_temperature":
                daily_fields.extend(["air_temperature_min", "air_temperature_max"])
            elif f in _FIELD_MAP:
                daily_fields.append(f)
            else:
                raise WeatherFieldNotSupported(f, self.provider_name())

        daily_fields = list(set(daily_fields))
        daily = await self.get_daily_data(latitude, longitude, start_date, end_date, daily_fields)

        n_days = daily.length
        n_hours = n_days * 24

        hourly_ts = np.array([
            daily.timestamps[i // 24].astype("datetime64[h]") + np.timedelta64(i % 24, "h")
            for i in range(n_hours)
        ])

        hourly_fields: dict[str, np.ndarray] = {}

        if "air_temperature" in fields:
            t_min = daily["air_temperature_min"] if "air_temperature_min" in daily else np.full(n_days, 10.0)
            t_max = daily["air_temperature_max"] if "air_temperature_max" in daily else np.full(n_days, 25.0)
            hourly_temp = np.zeros(n_hours)
            for d in range(n_days):
                for h in range(24):
                    phase = np.sin(np.pi * (h - 6) / 12.0)
                    avg = (float(t_min[d]) + float(t_max[d])) / 2.0
                    amp = (float(t_max[d]) - float(t_min[d])) / 2.0
                    hourly_temp[d * 24 + h] = avg + amp * phase
            hourly_fields["air_temperature"] = hourly_temp

        for f in fields:
            if f != "air_temperature" and f in daily:
                spread = np.repeat(daily[f], 24)
                if f == "precipitation":
                    spread = spread / 24.0
                hourly_fields[f] = spread

        return WeatherDataFrame(timestamps=hourly_ts, fields=hourly_fields)
