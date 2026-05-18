# Contributor Guide

## Adding a New Model

1. Choose the correct layer:
   - **Weather** (`models/weather/`): Raw accumulation (GDD, chill, precip)
   - **Agronomic** (`models/agronomic/`): Derived features (leaf wetness, VPD, phenology)
   - **Disease** (`models/disease/`): Risk assessment using lower-layer outputs

2. Create your model file and subclass `PestModelBase`:

```python
from agstack_pnd.foundation.base_model import PestModelBase
from agstack_pnd.foundation.types import ModelMetadata, ModelLayer, ModelResult, WeatherDataFrame
from uuid import UUID

class MyModel(PestModelBase):
    metadata = ModelMetadata(
        uuid=UUID("..."),  # Generate a unique UUID
        name="my_model",
        display_name="My Model",
        version="1.0.0",
        layer=ModelLayer.DISEASE,
        description="What this model does",
        supported_crops=["apple"],
        required_weather_fields=["air_temperature", "relative_humidity"],
        citation="Author (Year). Journal, vol, pages.",
    )

    def validate_parameters(self, parameters):
        return dict(parameters) if parameters else {}

    def calculate(self, weather_data, parameters=None, threat=None):
        # Your model logic here -- pure computation, no I/O
        ...
```

3. Register via entry point in `pyproject.toml`:

```toml
[project.entry-points."agstack_pnd.models"]
my_model = "agstack_pnd.models.disease.my_model:MyModel"
```

4. Write tests in `tests/unit/test_my_model.py` using the `seven_day_weather` fixture.

5. Add a citation to the model's `ModelMetadata`.

## Adding a New Weather Provider

Subclass `WeatherProvider` and implement all abstract methods. Map your provider's native field names to the standardized names in `STANDARD_WEATHER_FIELDS`.

## Adding a New Threat Definition

Add an entry to `src/agstack_pnd/catalog/data/pest_catalog.json` with:
- `scientific_name`, `common_name`, `threat_type`, `crop`
- `bio_params`: biological parameters (temperatures, streaks, phenology)
- `fuzzy_rules`: humidity/temp/rainfall ranges per risk level
- `special_rules`: any organism-specific logic

## Development Setup

```bash
git clone https://github.com/agstack/opensource-pestmodels.git
cd opensource-pestmodels
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v
```
