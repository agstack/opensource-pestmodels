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

## Three Ways to Use It

### 1. Python Library

```python
from agstack_pnd.models.disease.fuzzy_mamdani import FuzzyMamdaniRisk
from agstack_pnd.catalog.loader import get_threat

threat = get_threat("grape", "Botrytis cinerea")
model = FuzzyMamdaniRisk()
result = model.calculate(weather_data, threat=threat)

for score in result.daily_scores:
    print(f"{score.date}: {score.value:.0f}/100 ({score.risk_level.value})")
```

### 2. REST API

```bash
curl -X POST http://localhost:8000/api/v1/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "model_uuid": "a1b2c3d4-0004-4000-8000-000000000001",
    "latitude": 38.5, "longitude": -121.7,
    "crop": "grape",
    "threat_scientific_name": "Botrytis cinerea",
    "start_date": "2026-04-01",
    "end_date": "2026-05-01"
  }'
```

### 3. MCP Server (AI Agents)

The built-in [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server lets any AI agent -- Claude, GPT, Cursor, or custom LLMs -- discover and query pest/disease models programmatically.

**Start the server:**

```bash
pip install "agstack-pnd[server]"
uvicorn agstack_pnd.server.app:create_app --factory --port 8000
```

**Connect your AI agent** (Claude Desktop, Cursor, or any MCP client):

```json
{
  "mcpServers": {
    "agstack-pnd": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

**Available MCP tools:**

| Tool | What it does |
|------|-------------|
| `list_pest_models` | Discover models by layer or crop |
| `get_model_info` | Get metadata, parameters, and citations for a model |
| `get_supported_crops_tool` | List all crops with available models |
| `get_threats_for_crop_tool` | List pests/diseases for a specific crop |
| `explain_threat` | Get biological parameters for a crop-threat pairing |

**Example agent conversation:**
> **User:** "What diseases should I watch for in my grape vineyard this June?"
>
> **Agent** calls `get_threats_for_crop_tool("grape")` then `explain_threat("grape", "Uncinula necator")` and responds:
>
> "Watch for powdery mildew -- it thrives in warm, dry weather (20-28C). Unusually, free water actually *inhibits* this fungus. Your dry June increases powdery mildew risk while reducing downy mildew risk."

See the full [MCP Server Guide](docs/mcp_server_guide.md) for Claude Desktop config, Cursor config, stdio transport, Python client, and all tool/resource documentation.

## Architecture

```
                    +-----------+     +-----------+     +-------------+
                    |  Python   |     | REST API  |     | MCP Server  |
                    |  Library  |     | (FastAPI) |     | (AI Agents) |
                    +-----+-----+     +-----+-----+     +------+------+
                          |                 |                    |
                          v                 v                    v
                    +----------------------------------------------+
                    |           agstack_pnd Core Library            |
                    |                                              |
                    |  Layer 3: Fuzzy Mamdani | Rule-Based | UCIPM |
                    |  Layer 2: Leaf Wetness | VPD | Phenology     |
                    |  Layer 1: GDD | Chill Hours | Precipitation  |
                    |  Foundation: BaseModel ABC | WeatherProvider |
                    +----+--------+--------+--------+--------------+
                         |        |        |        |
                         v        v        v        v
                      NOAA    GeoID    Threat    PostgreSQL
                      API    Registry  Catalog     (cache)
```

Input: GeoID (AgStack Asset Registry) or raw lat/lon + crop + date range.
Output: daily risk scores (0-100) with Low / Moderate / High / Critical classification.

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
