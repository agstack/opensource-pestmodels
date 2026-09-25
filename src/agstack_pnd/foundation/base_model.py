"""Base model ABC -- every pest/disease model inherits from this."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from agstack_pnd.foundation.engine_params import EngineParamsBase
from agstack_pnd.foundation.types import (
    ModelMetadata,
    ModelResult,
    ThreatDefinition,
    WeatherDataFrame,
)


class PestModelBase(ABC):
    """Abstract base for all models in the three-layer hierarchy.

    Weather and agronomic models ignore the ``threat`` parameter.
    Disease models use it to load organism-specific biological parameters.
    """

    metadata: ClassVar[ModelMetadata]
    # Opt-in: models that accept typed engine params declare their schema here,
    # keyed for lookup by ModelRegistry.get_engine_params_schema(engine_type).
    engine_params_schema: ClassVar[type[EngineParamsBase] | None] = None

    @abstractmethod
    def calculate(
        self,
        weather_data: WeatherDataFrame,
        parameters: dict[str, object] | None = None,
        threat: ThreatDefinition | None = None,
    ) -> ModelResult:
        """Run the model on pre-fetched weather data.

        This method must be **pure computation** -- no network I/O.
        Weather data is fetched and injected by the caller (service layer
        or direct user code).

        Args:
            weather_data: Standardized hourly or daily weather observations.
            parameters: Model-specific overrides (e.g., GDD base temperature).
            threat: Organism-crop biological parameters (Layer 3 only).

        Returns:
            ModelResult with daily scores and summary statistics.
        """
        ...

    @abstractmethod
    def validate_parameters(self, parameters: dict[str, object] | None) -> dict[str, object]:
        """Validate and normalize parameters for this model.

        Returns the cleaned parameter dict (with defaults filled in).
        Raises ``ModelValidationError`` on invalid input.
        """
        ...

    def required_fields(self) -> list[str]:
        """Weather fields this model needs (from metadata)."""
        return list(self.metadata.required_weather_fields)
