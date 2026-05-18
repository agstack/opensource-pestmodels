# AgStack Pest & Disease Models

**Hierarchical pest and disease modeling framework** for the [AgStack Foundation](https://agstack.org) (Linux Foundation).

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Overview

`agstack-pnd` provides a composable, three-layer modeling framework for agricultural pest and disease risk assessment:

- **Layer 1 -- Weather/Accumulation**: Growing Degree Days, Chill Hours/Portions, Accumulated Precipitation
- **Layer 2 -- Agronomic/Derived**: Leaf Wetness Duration, VPD, Humidity Streaks, Phenological Gating
- **Layer 3 -- Disease/Pest Risk**: Fuzzy Mamdani risk engine, rule-based risk, UC IPM Powdery Mildew

Ships with **19 crops** and **54 crop-threat pairings** (21 diseases, 19 pests) from the OpenAgri catalog.

## Quick Start

```bash
# Install the core library
pip install agstack-pnd

# Install with server (FastAPI + MCP + PostgreSQL)
pip install "agstack-pnd[server]"

# Docker Compose (full service)
docker compose -f docker/compose.yaml up
```

## Usage

```python
from agstack_pnd.models.weather.growing_degree_days import GrowingDegreeDays
from agstack_pnd.foundation.types import WeatherDataFrame

model = GrowingDegreeDays()
result = model.calculate(weather_data, parameters={"base_temp": 10.0})
print(result.values)  # Daily GDD accumulation
```

## Architecture

```
WeatherProvider (NOAA)  -->  Layer 1 (GDD, Chill)
                              |
                              v
                         Layer 2 (Leaf Wetness, VPD, Phenology)
                              |
                              v
                         Layer 3 (Fuzzy Risk, Rule-Based, Disease Models)
                              |
                              v
                         ModelResult (daily scores, risk levels)
```

GeoID (AgStack Asset Registry) or raw lat/lon as input. REST API + MCP server for agents.

## Documentation

- [Executive Summary](docs/executive_summary.md)
- [Architecture Design](docs/design_architecture.md)
- [Contributor Guide](docs/contributor_guide.md)
- [Deployment Guide](docs/deployment_guide.md)
- [API Reference](https://agstack.github.io/opensource-pestmodels)

## Contributing

See the [Contributor Guide](docs/contributor_guide.md). Models are registered via Python entry points -- publish your model as a pip package and it auto-discovers.

## License

Apache-2.0. See [LICENSE](LICENSE).

## Acknowledgments

This project absorbs and supersedes:
- [agstack/pest-models](https://github.com/agstack/pest-models) (Agralogics weather models)
- [agstack/OpenAgri-PestAndDiseaseManagement](https://github.com/agstack/OpenAgri-PestAndDiseaseManagement) (OpenAgri PND service)
- [openagri-eu/OpenAgri-PestAndDiseaseManagement](https://github.com/openagri-eu/OpenAgri-PestAndDiseaseManagement) (OpenAgri fork with fuzzy risk)
