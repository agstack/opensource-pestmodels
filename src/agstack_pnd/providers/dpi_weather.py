"""DPI weather provider -- reads weather BITEs from Pancake.

This is the BITE-native data path: instead of calling a weather API directly,
agstack-pnd reads weather that Pancake's TAP runtime has already ingested into
the BITE store, keyed by GeoID. The control plane (AR2 identity + grant) governs
access; the data plane (MCP/HTTP) carries the payload.

BITE weather body contract (produced by the Pancake weather adapters):

    Body.sirup_data = {
        "timestamps": [ISO8601, ...],          # hourly
        "series": {"air_temperature": [...], "relative_humidity": [...],
                   "precipitation": [...], "wind_speed": [...], "dew_point": [...]},
        "daily": [{"date","t_min","t_max","precip","rh_mean","wind"}, ...],
    }

Because lookups are by GeoID, this provider is constructed with a ``geo_id``
(and optional field grant) rather than deriving one from lat/lon.
"""

from __future__ import annotations

from datetime import date, datetime

import httpx
import numpy as np

from agstack_pnd.foundation.exceptions import (
    WeatherFieldNotSupported,
    WeatherProviderError,
)
from agstack_pnd.foundation.types import WeatherDataFrame
from agstack_pnd.foundation.weather_provider import WeatherProvider

# Fields the DPI weather BITEs carry directly, plus daily-derived min/max.
_SERIES_FIELDS = [
    "air_temperature",
    "relative_humidity",
    "precipitation",
    "wind_speed",
    "dew_point",
]
_DAILY_DERIVED = ["air_temperature_min", "air_temperature_max"]
_SUPPORTED = _SERIES_FIELDS + _DAILY_DERIVED


class BiteWeatherProvider(WeatherProvider):
    """Weather provider backed by Pancake weather BITEs (GeoID-addressed)."""

    def __init__(
        self,
        geo_id: str,
        pancake_url: str = "http://localhost:8100",
        token: str | None = None,
        field_grant: str | None = None,
    ) -> None:
        if not geo_id:
            raise WeatherProviderError("BiteWeatherProvider requires a geo_id")
        self._geo_id = geo_id
        self._base_url = pancake_url.rstrip("/")
        self._token = token
        self._field_grant = field_grant

    def provider_name(self) -> str:
        return "AgStack DPI (Pancake weather BITEs)"

    def supported_fields(self) -> list[str]:
        return list(_SUPPORTED)

    async def _fetch_body(self, bite_type: str) -> dict | None:
        """Fetch the most recent weather BITE body of a given type for this GeoID."""
        headers: dict[str, str] = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        if self._field_grant:
            headers["X-Field-Grant"] = self._field_grant

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(
                    f"{self._base_url}/bites",
                    params={"geoid": self._geo_id, "type": bite_type, "limit": 1},
                    headers=headers,
                )
            except httpx.HTTPError as exc:
                raise WeatherProviderError(f"Pancake BITE query failed: {exc}") from exc

        if resp.status_code == 401:
            raise WeatherProviderError("Pancake rejected the request (missing/invalid hub token)")
        if resp.status_code == 403:
            raise WeatherProviderError("Field grant does not authorize this weather read")
        if resp.status_code != 200:
            raise WeatherProviderError(f"Pancake returned {resp.status_code}: {resp.text}")

        bites = resp.json().get("bites", [])
        if not bites:
            return None
        return bites[0].get("Body", {}).get("sirup_data")

    async def _resolve_body(self) -> dict:
        """Prefer historical weather; fall back to forecast."""
        body = await self._fetch_body("weather_historical")
        if body is None:
            body = await self._fetch_body("weather_forecast")
        if body is None:
            raise WeatherProviderError(
                f"No weather BITEs for GeoID '{self._geo_id}' in Pancake. "
                "Has the TAP worker ingested weather for this field?"
            )
        return body

    async def get_hourly_data(
        self,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
        fields: list[str],
    ) -> WeatherDataFrame:
        for f in fields:
            if f not in _SUPPORTED:
                raise WeatherFieldNotSupported(f, self.provider_name())

        body = await self._resolve_body()
        raw_ts = body.get("timestamps", [])
        series = body.get("series", {})
        if not raw_ts:
            raise WeatherProviderError("weather BITE has no timestamps")

        parsed = [datetime.fromisoformat(t) for t in raw_ts]
        keep = [
            i for i, dt in enumerate(parsed)
            if start_date <= dt.date() <= end_date
        ]
        if not keep:
            # Window outside the BITE coverage: use whatever the BITE holds.
            keep = list(range(len(parsed)))

        timestamps = np.array(
            [np.datetime64(parsed[i].replace(tzinfo=None)) for i in keep]
        )

        # Daily-derived fields need a per-hour lookup by date.
        daily_by_date = {d["date"]: d for d in body.get("daily", [])}

        field_arrays: dict[str, np.ndarray] = {}
        for f in fields:
            if f in series:
                vals = series[f]
                field_arrays[f] = np.array([float(vals[i]) for i in keep], dtype=np.float64)
            elif f in _DAILY_DERIVED:
                key = "t_min" if f == "air_temperature_min" else "t_max"
                field_arrays[f] = np.array(
                    [float(daily_by_date.get(parsed[i].date().isoformat(), {}).get(key, np.nan))
                     for i in keep],
                    dtype=np.float64,
                )
            else:  # pragma: no cover - guarded above
                raise WeatherFieldNotSupported(f, self.provider_name())

        return WeatherDataFrame(timestamps=timestamps, fields=field_arrays)

    async def get_daily_data(
        self,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
        fields: list[str],
    ) -> WeatherDataFrame:
        body = await self._resolve_body()
        daily = [
            d for d in body.get("daily", [])
            if start_date <= date.fromisoformat(d["date"]) <= end_date
        ] or body.get("daily", [])
        if not daily:
            raise WeatherProviderError("weather BITE has no daily records")

        timestamps = np.array([np.datetime64(d["date"]) for d in daily], dtype="datetime64[D]")
        field_map = {
            "air_temperature_min": "t_min",
            "air_temperature_max": "t_max",
            "precipitation": "precip",
            "relative_humidity": "rh_mean",
            "wind_speed": "wind",
        }
        field_arrays: dict[str, np.ndarray] = {}
        for f in fields:
            if f == "air_temperature":
                field_arrays[f] = np.array(
                    [(float(d["t_min"]) + float(d["t_max"])) / 2.0 for d in daily],
                    dtype=np.float64,
                )
            elif f in field_map:
                key = field_map[f]
                field_arrays[f] = np.array(
                    [float(d.get(key, np.nan)) for d in daily], dtype=np.float64
                )
            else:
                raise WeatherFieldNotSupported(f, self.provider_name())

        return WeatherDataFrame(timestamps=timestamps, fields=field_arrays)
