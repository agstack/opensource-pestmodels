"""Typed exception hierarchy for agstack-pnd."""

from __future__ import annotations


class PNDError(Exception):
    """Base exception for all agstack-pnd errors."""


class WeatherProviderError(PNDError):
    """Raised when a weather provider fails to fetch data."""


class WeatherFieldNotSupported(WeatherProviderError):
    """Raised when a requested weather field is not supported by the provider."""

    def __init__(self, field: str, provider: str) -> None:
        super().__init__(f"Field '{field}' is not supported by provider '{provider}'")
        self.field = field
        self.provider = provider


class GeoResolverError(PNDError):
    """Raised when GeoID resolution fails."""


class GeoIDNotFound(GeoResolverError):
    """Raised when a GeoID does not exist in the Asset Registry."""

    def __init__(self, geo_id: str) -> None:
        super().__init__(f"GeoID '{geo_id}' not found in AgStack Asset Registry")
        self.geo_id = geo_id


class ModelRegistryError(PNDError):
    """Raised on model registry lookup failures."""


class ModelNotFound(ModelRegistryError):
    """Raised when a model UUID is not in the registry."""

    def __init__(self, uuid: str) -> None:
        super().__init__(f"Model with UUID '{uuid}' not found in registry")
        self.uuid = uuid


class EngineTypeNotFound(ModelRegistryError):
    """Raised when no registered model declares the requested engine_type."""

    def __init__(self, engine_type: str) -> None:
        super().__init__(f"No registered model declares engine_type '{engine_type}'")
        self.engine_type = engine_type


class ThreatNotFound(PNDError):
    """Raised when a crop-threat pairing is not in the catalog."""

    def __init__(self, crop: str, threat: str) -> None:
        super().__init__(f"No threat definition for crop='{crop}', threat='{threat}'")
        self.crop = crop
        self.threat = threat


class ModelValidationError(PNDError):
    """Raised when model parameters fail validation."""


class InsufficientWeatherData(PNDError):
    """Raised when weather data is too short for the model's requirements."""

    def __init__(self, required_hours: int, available_hours: int) -> None:
        super().__init__(
            f"Model requires {required_hours} hours of data, "
            f"but only {available_hours} available"
        )
        self.required_hours = required_hours
        self.available_hours = available_hours
