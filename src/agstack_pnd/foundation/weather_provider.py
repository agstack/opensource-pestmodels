"""WeatherProvider ABC -- pluggable weather data source."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from agstack_pnd.foundation.types import WeatherDataFrame


class WeatherProvider(ABC):
    """Abstract interface for weather data providers.

    Implementations must map the standardized field names defined in
    ``agstack_pnd.foundation.types.STANDARD_WEATHER_FIELDS`` to their
    provider's native field names internally.

    The sole shipped provider is NOAA Climate Data Online. Community
    providers can be added by subclassing this ABC.
    """

    @abstractmethod
    async def get_hourly_data(
        self,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
        fields: list[str],
    ) -> WeatherDataFrame:
        """Fetch hourly weather data for a location and date range.

        Args:
            latitude: Decimal degrees (-90 to 90).
            longitude: Decimal degrees (-180 to 180).
            start_date: First day (inclusive).
            end_date: Last day (inclusive).
            fields: Standardized field names to retrieve.

        Returns:
            WeatherDataFrame with timestamps and requested fields.

        Raises:
            WeatherProviderError: On network or data errors.
            WeatherFieldNotSupported: If a requested field is unavailable.
        """
        ...

    @abstractmethod
    async def get_daily_data(
        self,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
        fields: list[str],
    ) -> WeatherDataFrame:
        """Fetch daily-aggregated weather data."""
        ...

    @abstractmethod
    def supported_fields(self) -> list[str]:
        """Return the list of standardized field names this provider can serve."""
        ...

    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name (e.g., 'NOAA Climate Data Online')."""
        ...
