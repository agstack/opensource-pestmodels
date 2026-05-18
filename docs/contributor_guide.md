# Contributor Guide

## Before You Start

- Read the [User Manual](user_manual.md) to understand the system
- Read the [Architecture Design](design_architecture.md) to understand the three-layer hierarchy
- All contributions must be Apache-2.0 compatible (see [LICENSE](../LICENSE))

## Development Setup

```bash
git clone https://github.com/agstack/opensource-pestmodels.git
cd opensource-pestmodels
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v
```

## What You Can Contribute

| Contribution type | Where it goes | Who reviews |
|-------------------|---------------|-------------|
| New weather/accumulation model | `src/agstack_pnd/models/weather/` | AgStack core maintainers |
| New agronomic/derived model | `src/agstack_pnd/models/agronomic/` | OpenAgri + AgStack maintainers |
| New disease/pest risk model | `src/agstack_pnd/models/disease/` | OpenAgri maintainers (required) |
| New threat definition (crop-pest pairing) | `src/agstack_pnd/catalog/data/pest_catalog.json` | OpenAgri maintainers (required) |
| New weather provider | `src/agstack_pnd/providers/` | AgStack core maintainers |
| New MCP tool | `src/agstack_pnd/server/mcp_server.py` | AgStack core maintainers |
| Bug fix | Wherever the bug is | Depends on area (see [CODEOWNERS](../.github/CODEOWNERS)) |
| Documentation | `docs/` | Both teams |

## Adding a New Model

1. **Choose the correct layer:**
   - **Weather** (`models/weather/`): Raw accumulation (GDD, chill, precip)
   - **Agronomic** (`models/agronomic/`): Derived features (leaf wetness, VPD, phenology)
   - **Disease** (`models/disease/`): Risk assessment using lower-layer outputs

2. **Create your model file** and subclass `PestModelBase`:

```python
from agstack_pnd.foundation.base_model import PestModelBase
from agstack_pnd.foundation.types import (
    ModelMetadata, ModelLayer, ModelResult, ThreatDefinition, WeatherDataFrame,
)
from uuid import UUID

class MyModel(PestModelBase):
    metadata = ModelMetadata(
        uuid=UUID("..."),  # Generate with: python -c "import uuid; print(uuid.uuid4())"
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
        params = self.validate_parameters(parameters)
        # Your model logic here -- pure computation, no I/O
        ...
```

3. **Register via entry point** in `pyproject.toml`:

```toml
[project.entry-points."agstack_pnd.models"]
my_model = "agstack_pnd.models.disease.my_model:MyModel"
```

4. **Write tests** in `tests/unit/test_my_model.py` using the `seven_day_weather` or `thirty_day_weather` fixtures from `conftest.py`.

5. **Add a citation** to the model's `ModelMetadata`. This is required for all disease models (guardrail G-MODEL-001).

## Adding a New Threat Definition

Add an entry to `src/agstack_pnd/catalog/data/pest_catalog.json`:

```json
{
  "scientific_name": "Venturia inaequalis",
  "common_name": "Apple scab",
  "threat_type": "fungus",
  "crop": "apple",
  "bio_params": {
    "t_base": 0.0,
    "t_lethal_min": -5.0,
    "t_lethal_max": 40.0,
    "t_optimal_min": 15.0,
    "t_optimal_max": 24.0,
    "min_streak": 3,
    "min_wetness_hours_critical": 20.0,
    "min_wetness_hours_high": 14.0
  },
  "fuzzy_rules": [
    {"hum_lo": 90, "hum_hi": 100, "temp_lo": 15, "temp_hi": 24, "rain_min": 2.0, "risk_level": "critical"},
    {"hum_lo": 80, "hum_hi": 100, "temp_lo": 10, "temp_hi": 28, "rain_min": 1.0, "risk_level": "high"},
    {"hum_lo": 70, "hum_hi": 90, "temp_lo": 6, "temp_hi": 30, "rain_min": 0.0, "risk_level": "moderate"},
    {"hum_lo": 0, "hum_hi": 70, "temp_lo": 0, "temp_hi": 35, "rain_min": 0.0, "risk_level": "low"}
  ],
  "special_rules": {}
}
```

All biological parameters must reference published literature (guardrail G-MODEL-003). OpenAgri maintainers review all threat catalog changes.

## Adding a New Weather Provider

Subclass `WeatherProvider` in `src/agstack_pnd/providers/`:

```python
from agstack_pnd.foundation.weather_provider import WeatherProvider
from agstack_pnd.foundation.types import WeatherDataFrame

class MyProvider(WeatherProvider):
    async def get_hourly_data(self, latitude, longitude, start_date, end_date, fields):
        # Map standardized field names to your provider's native names
        # Fetch data and return as WeatherDataFrame
        ...

    async def get_daily_data(self, latitude, longitude, start_date, end_date, fields):
        ...

    def supported_fields(self):
        return ["air_temperature", "relative_humidity", ...]

    def provider_name(self):
        return "My Weather Service"
```

See `src/agstack_pnd/providers/noaa.py` for a complete reference implementation.

## Pull Request Process

### What happens when you open a PR

1. **Four automated CI gates run** (all must pass before merge):

| Gate | What it checks |
|------|----------------|
| Gate 1: Lint & Format | `ruff check` + `ruff format` |
| Gate 2: Type Check | `mypy --strict` |
| Gate 3: Tests | `pytest` -- all unit and integration tests |
| Gate 4: Catalog & FATFD | Threat catalog schema, UUID uniqueness, FATFD validator |

2. **CODEOWNERS review is requested** based on which files you changed:
   - Disease models, agronomic models, threat catalog -> OpenAgri maintainers must approve
   - Foundation, providers, CI/CD -> AgStack core maintainers must approve
   - See [CODEOWNERS](../.github/CODEOWNERS) for the full mapping

3. **Once all gates pass AND reviewers approve**, the PR can be merged.

### Tips for a smooth review

- Run `pytest tests/ -v` locally before pushing
- Run `ruff check src/ tests/ && ruff format --check src/ tests/` to catch lint issues
- Include a citation for any new disease model
- Add tests that verify expected outputs for known weather conditions
- Keep PRs focused -- one model or one threat definition per PR is ideal

## Exposing a New MCP Tool

If your contribution should be queryable by AI agents, add a tool to `src/agstack_pnd/server/mcp_server.py`. See the [MCP Server Guide](mcp_server_guide.md) for details.

## Related Documentation

- [User Manual](user_manual.md) -- How to use models, API, and MCP
- [MCP Server Guide](mcp_server_guide.md) -- AI agent integration
- [Architecture Design](design_architecture.md) -- Technical architecture
- [OpenAgri Migration Guide](openagri_migration.md) -- OpenAgri team's role as maintainers
- [Deployment Guide](deployment_guide.md) -- Running the server
