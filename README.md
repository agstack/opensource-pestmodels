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
print(f"Total GDD: {result.summary['total_gdd']}")  # Cumulative GDD
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

- [User Manual](docs/user_manual.md) -- How to use the library, API, and MCP server
- [MCP Server Guide](docs/mcp_server_guide.md) -- Install and connect AI agents to pest/disease models
- [Executive Summary](docs/executive_summary.md) -- Vision, stakeholders, coverage
- [Architecture Design](docs/design_architecture.md) -- Technical architecture
- [OpenAgri Migration Guide](docs/openagri_migration.md) -- How OpenAgri's work evolves into this framework
- [Contributor Guide](docs/contributor_guide.md) -- How to add models and providers
- [Deployment Guide](docs/deployment_guide.md) -- Docker, environment variables
- [API Reference](https://agstack.github.io/opensource-pestmodels)

## Contributing and CI/CD Quality Gates

Every contribution goes through **four automated CI gates** and **human review** before it can be merged. No code reaches `master` without passing all of them.

### Automated Gates (GitHub Actions)

| Gate | What it checks | Why it matters |
|------|---------------|----------------|
| **1. Lint & Format** | `ruff check` + `ruff format` | Consistent code style across all contributors |
| **2. Type Check** | `mypy --strict` | Catches type errors before they become runtime bugs |
| **3. Tests** | `pytest` -- all unit and integration tests | Every model must produce correct, reproducible results |
| **4. Catalog & FATFD Integrity** | Threat catalog schema, model UUID uniqueness, FATFD validator | Biological parameters are valid; no duplicate model IDs; quality harness passes |

All four gates must pass before a PR can be merged. This is enforced through GitHub branch protection rules.

### Human Review (CODEOWNERS)

Different parts of the codebase have designated reviewers:

- **Threat catalog and disease models** -- Reviewed by [OpenAgri maintainers](docs/openagri_migration.md) who created the original biological parameters and fuzzy risk engine
- **Foundation, infrastructure, CI/CD** -- Reviewed by AgStack core maintainers
- **Documentation** -- Reviewed by both teams

See [CODEOWNERS](.github/CODEOWNERS) for the full mapping.

### How to Contribute

1. Fork the repo and create a branch
2. Make your changes (new model, threat definition, bug fix)
3. Ensure tests pass locally: `pytest tests/ -v`
4. Open a Pull Request -- CI gates run automatically
5. Address review feedback from the designated CODEOWNERS
6. Once all gates pass and reviewers approve, the PR is merged

See the full [Contributor Guide](docs/contributor_guide.md) for details on adding models, weather providers, and threat definitions.

### Release Process

Releases are triggered by git tags (`v*`). When a maintainer tags a release:
1. The wheel is built and published to **PyPI** (`pip install agstack-pnd`)
2. A Docker image is built and pushed to **GHCR** (`ghcr.io/agstack/opensource-pestmodels`)
3. Documentation is rebuilt and deployed to **GitHub Pages**

## Relationship to OpenAgri

This project is the **evolution** of the OpenAgri Pest and Disease Management service, not a replacement. The OpenAgri team's Fuzzy Mamdani risk engine, threat catalog (19 crops, 54 threats), and biological parameters form the scientific core of this framework. OpenAgri maintainers serve as domain reviewers for all contributions touching disease models and biological parameters.

See [OpenAgri Migration Guide](docs/openagri_migration.md) for the full story.

## License

Apache-2.0. See [LICENSE](LICENSE).

## Acknowledgments

This project builds on the pioneering work of:
- **[OpenAgri (Horizon Europe)](https://horizon-openagri.eu/)** -- Fuzzy Mamdani risk engine, 54 crop-threat definitions, leaf wetness estimation. Special thanks to Stefan Drobic (VizLore), Nikos Kalatzis (Green Supply Chain), and Agrobit S.r.l.
- **[agstack/pest-models](https://github.com/agstack/pest-models)** -- Original GDD, chill, leaf wetness, and powdery mildew models
- **[agstack/OpenAgri-PestAndDiseaseManagement](https://github.com/agstack/OpenAgri-PestAndDiseaseManagement)** -- FastAPI service architecture, GDD intervals, rule-based risk engine
