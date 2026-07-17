"""Pydantic Settings for server configuration."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "PND_"}

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/pnd"
    noaa_api_token: str = ""
    agstack_registry_url: str = "https://api-ar.agstack.org"
    agstack_registry_token: str = ""
    cors_origins: list[str] = ["*"]
    debug: bool = False

    # Weather source: "dpi" reads weather BITEs from Pancake; "noaa" uses NOAA CDO.
    weather_provider: str = "noaa"
    # Pancake grants/BITE service base URL (DPI data plane).
    pancake_url: str = "http://localhost:8100"
    # Optional hub bearer token for authenticating to Pancake /bites in dev.
    pancake_token: str = ""
    # When set, agstack-pnd publishes PEST_DISEASE risk BITEs back to Pancake.
    publish_risk_bites: bool = False


settings = Settings()
