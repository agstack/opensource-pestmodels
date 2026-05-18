# User Manual: AgStack Pest & Disease Models

## Table of Contents

1. [Getting Started](#getting-started)
2. [Installation](#installation)
3. [Core Concepts](#core-concepts)
4. [Using the Library (Python)](#using-the-library-python)
5. [Using the REST API](#using-the-rest-api)
6. [Using the MCP Server (AI Agents)](#using-the-mcp-server-ai-agents)
7. [Supported Crops and Threats](#supported-crops-and-threats)
8. [Model Reference](#model-reference)
9. [Working with GeoIDs](#working-with-geoids)
10. [Common Workflows](#common-workflows)
11. [Troubleshooting](#troubleshooting)

---

## Getting Started

`agstack-pnd` answers one question: **"Given a field, a crop, and a date range, what is the probability of pest or disease damage?"**

You provide:
- A **location** (AgStack GeoID or latitude/longitude)
- A **crop** (from 19 supported crops)
- A **date range** (start and end dates)
- Optionally, a specific **threat** (pest or disease organism)

You receive:
- **Daily risk scores** (0-100 continuous scale)
- **Risk classifications** (Low / Moderate / High / Critical)
- **Summary statistics** (max score, days at each risk level)

There are three ways to use the system:
1. **Python library** -- `pip install agstack-pnd` and call models directly
2. **REST API** -- Deploy the FastAPI server and query over HTTP
3. **MCP server** -- Connect AI agents via the Model Context Protocol

---

## Installation

### Library only (for scripting, notebooks, research)

```bash
pip install agstack-pnd
```

### Full server (REST API + MCP + PostgreSQL)

```bash
pip install "agstack-pnd[server]"
```

### Docker Compose (recommended for production)

```bash
git clone https://github.com/agstack/opensource-pestmodels.git
cd opensource-pestmodels/docker
cp .env.example .env
# Edit .env -- add your NOAA API token
docker compose up -d
```

The API will be at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

### Development install

```bash
git clone https://github.com/agstack/opensource-pestmodels.git
cd opensource-pestmodels
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v
```

---

## Core Concepts

### Three-Layer Model Hierarchy

Models are organized in three layers that build on each other:

```
Layer 1: Weather / Accumulation
    Input: raw weather data (temperature, humidity, rainfall, wind)
    Output: accumulated values (GDD, chill hours, cumulative precipitation)

Layer 2: Agronomic / Derived Features
    Input: raw weather data + Layer 1 outputs
    Output: derived features (leaf wetness hours, VPD, humidity streaks, phenology stage)

Layer 3: Disease / Pest Risk
    Input: raw weather data + Layer 1 & 2 outputs + threat definition
    Output: daily risk scores (0-100) with risk level classifications
```

### Threat Definitions

A **threat definition** describes a specific organism-crop pairing with biological parameters:
- Temperature thresholds (base, lethal, optimal)
- Humidity and wetness requirements
- Phenological windows (when the organism is active during the season)
- Fuzzy rules mapping weather conditions to risk levels
- Special rules (e.g., Mills table for apple scab, Goidanich rule for downy mildew)

### UUIDs

Every model has a permanent UUID. Once assigned, a UUID never changes. You can reference models by UUID in API calls and they will always resolve to the same model (though the version may update).

### Weather Provider

All weather data comes through the `WeatherProvider` interface. NOAA Climate Data Online is the shipped provider. The system uses standardized field names internally, so models never need to know which provider supplied the data.

---

## Using the Library (Python)

### Running a simple weather model

```python
from agstack_pnd.models.weather.growing_degree_days import GrowingDegreeDays
from agstack_pnd.foundation.types import WeatherDataFrame
import numpy as np

# Create synthetic weather data (or fetch from NOAA)
n_hours = 7 * 24  # 7 days
timestamps = np.array([
    np.datetime64("2026-05-01") + np.timedelta64(h, "h")
    for h in range(n_hours)
])
temps = 15.0 + 8.0 * np.sin(np.pi * np.arange(n_hours) / 12.0)

weather = WeatherDataFrame(
    timestamps=timestamps,
    fields={"air_temperature": temps},
)

# Run the model
model = GrowingDegreeDays()
result = model.calculate(weather, parameters={"base_temp": 10.0})

print(f"Total GDD: {result.summary['total_gdd']}")
for score in result.daily_scores:
    print(f"  {score.date}: {score.value} GDD (cumulative)")
```

### Running a disease risk model

```python
from agstack_pnd.models.disease.fuzzy_mamdani import FuzzyMamdaniRisk
from agstack_pnd.catalog.loader import get_threat

# Load the threat definition for grape downy mildew
threat = get_threat("grape", "Plasmopora viticola")

# Run the fuzzy risk engine (weather_data must include
# air_temperature, relative_humidity, and precipitation)
model = FuzzyMamdaniRisk()
result = model.calculate(weather_data, threat=threat)

print(f"Crop: {result.summary['crop']}")
print(f"Threat: {result.summary['threat']}")
print(f"Max risk score: {result.summary['max_score']}")
print(f"Days at Critical: {result.summary['days_critical']}")
print(f"Days at High: {result.summary['days_high']}")

for score in result.daily_scores:
    print(f"  {score.date}: {score.value:.1f} ({score.risk_level.value})")
```

### Fetching weather from NOAA

```python
import asyncio
from datetime import date
from agstack_pnd.providers.noaa import NOAAProvider

async def fetch():
    provider = NOAAProvider(api_token="your-noaa-token")
    weather = await provider.get_hourly_data(
        latitude=38.5,
        longitude=-121.7,
        start_date=date(2026, 4, 1),
        end_date=date(2026, 5, 1),
        fields=["air_temperature", "relative_humidity", "precipitation"],
    )
    return weather

weather_data = asyncio.run(fetch())
```

### Discovering available models

```python
from agstack_pnd.foundation.model_registry import ModelRegistry

registry = ModelRegistry()

# List all models
for model in registry.list_models():
    print(f"{model.display_name} ({model.layer.value}) -- UUID: {model.uuid}")

# Filter by layer
weather_models = registry.list_models(layer="weather")

# Filter by crop
grape_models = registry.list_models(crop="grape")

# Get a model by UUID
from uuid import UUID
model = registry.get_model(UUID("a1b2c3d4-0004-4000-8000-000000000001"))
```

### Browsing the threat catalog

```python
from agstack_pnd.catalog.loader import list_crops, list_threats, get_threat

# All supported crops (from the bundled seed catalog)
print(list_crops())
# ['apple', 'coffee', 'grape', 'olive', 'pear', ...]  # expands as catalog grows

# All threats for grape
for t in list_threats("grape"):
    print(f"  {t.common_name} ({t.scientific_name}) -- {t.threat_type.value}")

# Specific threat with biological parameters
threat = get_threat("apple", "Venturia inaequalis")
print(f"Base temp: {threat.bio_params.t_base}C")
print(f"Lethal range: {threat.bio_params.t_lethal_min} to {threat.bio_params.t_lethal_max}C")
print(f"Optimal range: {threat.bio_params.t_optimal_min} to {threat.bio_params.t_optimal_max}C")
print(f"Fuzzy rules: {len(threat.fuzzy_rules)}")
print(f"Special rules: {threat.special_rules}")
```

### Using GeoID to resolve field location

```python
import asyncio
from agstack_pnd.foundation.geo_resolver import GeoResolver

async def resolve():
    resolver = GeoResolver()
    location = await resolver.resolve("your-64-char-geoid-here")
    print(f"Lat: {location.latitude}, Lon: {location.longitude}")
    return location

# Or use raw coordinates (no GeoID needed)
location = GeoResolver.from_coordinates(latitude=38.5, longitude=-121.7)
```

---

## Using the REST API

### Start the server

```bash
# With environment variables
export PND_NOAA_API_TOKEN=your-token
uvicorn agstack_pnd.server.app:create_app --factory --host 0.0.0.0 --port 8000

# Or with Docker
docker compose -f docker/compose.yaml up -d
```

### Endpoints

#### List all models
```bash
curl http://localhost:8000/api/v1/models
curl http://localhost:8000/api/v1/models?layer=disease
curl http://localhost:8000/api/v1/models?crop=grape
```

#### Get model details
```bash
curl http://localhost:8000/api/v1/models/a1b2c3d4-0004-4000-8000-000000000001
```

#### List crops and threats
```bash
curl http://localhost:8000/api/v1/crops
curl http://localhost:8000/api/v1/crops/grape/threats
curl http://localhost:8000/api/v1/threats
curl http://localhost:8000/api/v1/threats?crop=apple
```

#### Run a calculation

```bash
curl -X POST http://localhost:8000/api/v1/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "model_uuid": "a1b2c3d4-0004-4000-8000-000000000001",
    "latitude": 38.5,
    "longitude": -121.7,
    "crop": "grape",
    "threat_scientific_name": "Plasmopora viticola",
    "start_date": "2026-04-01",
    "end_date": "2026-05-01"
  }'
```

#### Using GeoID instead of coordinates

```bash
curl -X POST http://localhost:8000/api/v1/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "model_uuid": "a1b2c3d4-0004-4000-8000-000000000001",
    "geo_id": "your-64-char-geoid-here",
    "crop": "grape",
    "threat_scientific_name": "Botrytis cinerea",
    "start_date": "2026-06-01",
    "end_date": "2026-07-01"
  }'
```

#### Health checks
```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

### Response format

All calculation responses follow this structure:

```json
{
  "model_uuid": "a1b2c3d4-0004-4000-8000-000000000001",
  "model_name": "fuzzy_mamdani_risk",
  "computed_at": "2026-05-17T12:00:00Z",
  "start_date": "2026-04-01",
  "end_date": "2026-05-01",
  "daily_scores": [
    {"date": "2026-04-01", "value": 23.5, "risk_level": "low"},
    {"date": "2026-04-02", "value": 45.2, "risk_level": "moderate"},
    {"date": "2026-04-03", "value": 72.8, "risk_level": "high"}
  ],
  "summary": {
    "threat": "Downy mildew",
    "crop": "grape",
    "max_score": 72.8,
    "days_critical": 0,
    "days_high": 5,
    "days_moderate": 12,
    "days_low": 14
  }
}
```

---

## Using the MCP Server (AI Agents)

The MCP (Model Context Protocol) server allows AI agents (Claude, GPT, open-source LLMs) to discover and query pest/disease models programmatically.

### Available MCP tools

| Tool | Description |
|------|-------------|
| `list_pest_models` | List all models, filter by layer or crop |
| `get_model_info` | Get metadata and parameter schema for a model UUID |
| `get_supported_crops_tool` | List all crops with available models |
| `get_threats_for_crop_tool` | List threats for a specific crop |
| `explain_threat` | Get biological parameters for a crop-threat pairing |

### Available MCP resources

| Resource URI | Description |
|-------------|-------------|
| `pnd://models` | Full model catalog (markdown) |
| `pnd://crops` | Supported crops with threat counts |

### Connecting to the MCP server

The MCP server is mounted on the FastAPI app. When using Streamable HTTP transport, connect to `http://localhost:8000/mcp`.

Example MCP client configuration:

```json
{
  "mcpServers": {
    "agstack-pnd": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

### What an agent conversation looks like

An AI agent can use MCP to:
1. Call `get_supported_crops_tool()` to see what crops are available
2. Call `get_threats_for_crop_tool("grape")` to see threats for grape
3. Call `explain_threat("grape", "Botrytis cinerea")` to understand the organism
4. Call `list_pest_models(layer="disease")` to find available risk engines
5. Use the REST API `/calculate` endpoint to run a model with specific parameters

---

## Supported Crops and Threats

### Crops (19 total)

Almond, Apple, Apricot, Avocado, Banana, Cherry, Citrus, Cocoa, Coffee, Grape, Guava, Hazelnut, Mango, Olive, Papaya, Peach, Pear, Pistachio, Plum

### Shipped threat catalog (representative entries)

| Crop | Threat | Type | Special Rules |
|------|--------|------|---------------|
| Apple | Apple scab (*Venturia inaequalis*) | Fungus | Mills table infection periods |
| Apple | Codling moth (*Cydia pomonella*) | Insect | GDD flight windows (250/468/900) |
| Grape | Downy mildew (*Plasmopora viticola*) | Oomycete | Goidanich rule (T>11C + RH>90% + rain>10mm) |
| Grape | Powdery mildew (*Uncinula necator*) | Fungus | Free water INHIBITS infection |
| Grape | Grey mold (*Botrytis cinerea*) | Fungus | Two-fifteens rule (15C + 15h wetness) |
| Coffee | Coffee leaf rust (*Hemileia vastatrix*) | Fungus | 24h free water required |
| Pear | Fire blight (*Erwinia amylovora*) | Bacterium | Maryblyt/Cougarblight model |
| Olive | Olive fly (*Bactrocera oleae*) | Insect | Temperature-driven generation timing |

The catalog is extensible -- add entries to `src/agstack_pnd/catalog/data/pest_catalog.json`.

---

## Model Reference

### Layer 1: Weather / Accumulation

| Model | UUID (short) | Input Fields | Parameters |
|-------|-------------|--------------|------------|
| Growing Degree Days | `..0001-..01` | air_temperature | `base_temp` (default 10C), `upper_threshold` (default 50C) |
| Chill Hours (Utah) | `..0002-..01` | air_temperature | none |
| Chill Hours (32-45) | `..0002-..02` | air_temperature | none |
| Chill Portions | `..0002-..03` | air_temperature | none |
| Accumulated Precipitation | `..0001-..02` | precipitation | `window_days` (3, 7, 10, or 14) |

### Layer 2: Agronomic / Derived

| Model | UUID (short) | Input Fields | Parameters |
|-------|-------------|--------------|------------|
| Leaf Wetness (CART) | `..0003-..01` | air_temperature, dew_point, relative_humidity, wind_speed | none |
| Leaf Wetness (RH) | `..0003-..02` | relative_humidity, precipitation | none |
| VPD | `..0003-..03` | air_temperature, relative_humidity | none |
| Humidity Streak | `..0003-..04` | relative_humidity | `rh_threshold` (default 80%) |
| Phenological Gating | `..0003-..05` | air_temperature | `base_temp` (default 5C), uses threat.bio_params |

### Layer 3: Disease / Pest Risk

| Model | UUID (short) | Input Fields | Requires Threat |
|-------|-------------|--------------|-----------------|
| Fuzzy Mamdani Risk | `..0004-..01` | air_temperature, relative_humidity, precipitation | Yes (any crop-threat) |
| Rule-Based Risk | `..0004-..02` | air_temperature, relative_humidity, precipitation | No (rules in parameters) |
| Powdery Mildew Grape | `..0004-..03` | air_temperature, dew_point, relative_humidity, wind_speed | No (grape-specific) |

---

## Working with GeoIDs

AgStack GeoIDs are 64-character SHA-256 hex strings that uniquely identify agricultural field boundaries. They are generated by the [AgStack Asset Registry](https://github.com/agstack/asset-registry).

### Register a field (one-time, via Asset Registry)

```bash
curl -X POST https://api-ar.agstack.org/register-field-boundary \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"wkt": "POLYGON((-121.7 38.5, -121.7 38.6, -121.6 38.6, -121.6 38.5, -121.7 38.5))"}'
```

Response includes the GeoID, which you then use in all agstack-pnd queries.

### Use GeoID in calculations

The system resolves GeoID to coordinates automatically:

```python
# Python
result = await calculate(
    model_uuid="...",
    geo_id="abc123...",  # 64-char GeoID
    crop="grape",
    ...
)
```

```bash
# REST API
curl -X POST http://localhost:8000/api/v1/calculate \
  -d '{"model_uuid": "...", "geo_id": "abc123...", "crop": "grape", ...}'
```

### Fallback to lat/lon

If you don't have a GeoID, raw coordinates always work:

```python
result = await calculate(
    model_uuid="...",
    latitude=38.5,
    longitude=-121.7,
    crop="grape",
    ...
)
```

---

## Common Workflows

### Workflow 1: "What diseases threaten my grape vineyard this month?"

```python
from agstack_pnd.catalog.loader import list_threats, get_threat
from agstack_pnd.models.disease.fuzzy_mamdani import FuzzyMamdaniRisk

# See all grape threats
threats = list_threats("grape")
model = FuzzyMamdaniRisk()

for threat_def in threats:
    result = model.calculate(weather_data, threat=threat_def)
    max_risk = max(s.value for s in result.daily_scores)
    print(f"{threat_def.common_name}: max score {max_risk:.0f} ({result.summary.get('days_high', 0)} high-risk days)")
```

### Workflow 2: "Track GDD accumulation for codling moth flight prediction"

```python
from agstack_pnd.models.weather.growing_degree_days import GrowingDegreeDays
from agstack_pnd.catalog.loader import get_threat

threat = get_threat("apple", "Cydia pomonella")
base_temp = threat.bio_params.t_base  # 10.0C
flight_gdd = threat.special_rules.get("gdd_flight_windows", {})

model = GrowingDegreeDays()
result = model.calculate(weather_data, {"base_temp": base_temp})

for score in result.daily_scores:
    if score.value >= flight_gdd.get("first_flight", 250):
        print(f"First flight expected around {score.date}")
        break
```

### Workflow 3: "Batch risk assessment for multiple fields"

```python
import asyncio
from agstack_pnd.foundation.geo_resolver import GeoResolver
from agstack_pnd.providers.noaa import NOAAProvider

async def assess_fields(geo_ids, crop, threat_name):
    resolver = GeoResolver()
    provider = NOAAProvider("your-token")
    model = FuzzyMamdaniRisk()
    threat = get_threat(crop, threat_name)

    for geo_id in geo_ids:
        location = await resolver.resolve(geo_id)
        weather = await provider.get_hourly_data(
            location.latitude, location.longitude,
            start_date, end_date,
            model.required_fields(),
        )
        result = model.calculate(weather, threat=threat)
        print(f"Field {geo_id[:12]}...: max risk {result.summary['max_score']:.0f}")
```

---

## Troubleshooting

### "NOAA API token not configured"

Set the environment variable:
```bash
export PND_NOAA_API_TOKEN=your-token
```
Get a free token at https://www.ncdc.noaa.gov/cdo-web/token (emailed instantly).

### "No NOAA data for location"

NOAA CDO coverage varies by region. Try:
- Expanding the date range
- Checking that coordinates are correct (decimal degrees, lat -90 to 90, lon -180 to 180)
- Using a location closer to a NOAA weather station

### "FuzzyMamdaniRisk requires a ThreatDefinition"

Layer 3 disease models need a threat definition. Load one from the catalog:
```python
from agstack_pnd.catalog.loader import get_threat
threat = get_threat("grape", "Botrytis cinerea")
result = model.calculate(weather_data, threat=threat)
```

### "GeoID not found"

The GeoID must be registered in the AgStack Asset Registry first. Use raw lat/lon as fallback:
```python
location = GeoResolver.from_coordinates(38.5, -121.7)
```

### "Model with UUID not found"

Ensure the package is installed (`pip install agstack-pnd`). Third-party models need their own package installed. Check available models:
```python
from agstack_pnd.foundation.model_registry import ModelRegistry
for m in ModelRegistry().list_models():
    print(f"{m.name}: {m.uuid}")
```

---

## Getting Help

- **GitHub Issues**: https://github.com/agstack/opensource-pestmodels/issues
- **AgStack Foundation**: https://agstack.org
- **Documentation**: https://agstack.github.io/opensource-pestmodels
