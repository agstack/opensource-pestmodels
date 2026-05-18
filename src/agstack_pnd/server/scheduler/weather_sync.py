"""Weather sync job -- pre-fetches NOAA data for registered parcels."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def sync_weather_for_parcels() -> None:
    """Fetch latest weather data for all registered parcels.

    Called by APScheduler cron. Populates the weather_cache table
    so that model calculations are fast (cache hits).
    """
    # TODO: query parcels, fetch NOAA data, upsert weather_cache
    logger.info("Weather sync: placeholder -- implement with DB + NOAA provider")
