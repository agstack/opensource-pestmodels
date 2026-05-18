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


settings = Settings()
