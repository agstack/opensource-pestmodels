# Design Architecture: AgStack Pest & Disease Models

## 1. Architecture Overview

```
                    +-----------+     +-----------+     +------------+
                    |  CLI /    |     | REST API  |     | MCP Server |
                    |  Scripts  |     | (FastAPI) |     | (FastMCP)  |
                    +-----+-----+     +-----+-----+     +-----+------+
                          |                 |                   |
                          v                 v                   v
                    +--------------------------------------------+
                    |          agstack_pnd  Core Library          |
                    |                                            |
                    |  Layer 3: Disease/Pest Risk Models          |
                    |    FuzzyMamdani | RuleBased | PowderyMildew |
                    |         |                                   |
                    |  Layer 2: Agronomic/Derived                 |
                    |    LeafWetness | VPD | HumidityStreak | Phen|
                    |         |                                   |
                    |  Layer 1: Weather/Accumulation              |
                    |    GDD | ChillHours | ChillPortions | Precip|
                    |         |                                   |
                    |  Foundation                                 |
                    |    BaseModel ABC | WeatherProvider ABC      |
                    |    ModelRegistry | GeoResolver | Types      |
                    +----+------+------+------+------------------+
                         |      |      |      |
                         v      v      v      v
                    +------+ +------+ +------+ +------+
                    | NOAA | |GeoID | | Threat | | DB   |
                    | API  | |Regis.| | Catalog| |(PG)  |
                    +------+ +------+ +------+ +------+
```

## 2. Package Structure

```
src/agstack_pnd/
    __init__.py                          # __version__
    foundation/                          # ABCs, types, registry
        base_model.py                    # PestModelBase ABC
        weather_provider.py              # WeatherProvider ABC
        geo_resolver.py                  # GeoID -> coordinates
        model_registry.py               # UUID catalog + entry-point discovery
        types.py                         # WeatherDataFrame, ModelResult, ThreatDefinition, etc.
        exceptions.py                    # Typed error hierarchy
    models/
        weather/                         # Layer 1
            growing_degree_days.py
            chill_hours.py
            chill_portions.py
            accumulated_precip.py
        agronomic/                       # Layer 2
            leaf_wetness_cart.py
            leaf_wetness_rh.py
            vpd.py
            humidity_streak.py
            phenology.py
        disease/                         # Layer 3
            fuzzy_mamdani.py
            rule_based.py
            powdery_mildew_grape.py
    providers/
        noaa.py                          # NOAA CDO provider
    catalog/
        loader.py                        # Threat catalog loader
        crops.py                         # Crop registry
        threats.py                       # Threat accessors
        data/pest_catalog.json           # 54 crop-threat pairings
    server/                              # Optional service layer
        app.py                           # FastAPI factory
        config.py                        # Pydantic Settings
        mcp_server.py                    # MCP tools + resources
        routers/                         # API endpoints
        db/                              # SQLAlchemy + Alembic
        scheduler/                       # Background NOAA sync
```

## 3. Core Abstractions

### PestModelBase ABC

Every model inherits from `PestModelBase`. Key contract:

- `metadata: ClassVar[ModelMetadata]` -- UUID, name, layer, supported crops, required fields, citations
- `calculate(weather_data, parameters, threat) -> ModelResult` -- Pure computation, no I/O
- `validate_parameters(parameters) -> dict` -- Input validation with defaults

### WeatherProvider ABC

- `get_hourly_data(lat, lon, start, end, fields) -> WeatherDataFrame`
- `get_daily_data(lat, lon, start, end, fields) -> WeatherDataFrame`
- `supported_fields() -> list[str]`

### ThreatDefinition

Carries organism-specific biological parameters for disease models:
- `bio_params`: t_base, t_lethal_min/max, t_optimal_min/max, min_streak, phenology windows
- `fuzzy_rules`: humidity/temp/rainfall ranges per risk level
- `special_rules`: organism-specific logic (Goidanich, Mills, two-fifteens, etc.)

### ModelRegistry

UUID-based catalog with Python entry-point auto-discovery:
- `list_models(layer, crop)` -- Discover models
- `get_model(uuid)` -- Instantiate by UUID
- Third-party packages register via `[project.entry-points."agstack_pnd.models"]`

## 4. Three-Layer Hierarchy

### Layer 1: Weather/Accumulation
- GDD (multi-base: 0/5/10C + custom)
- Chill Hours (Utah + 32-45)
- Chill Portions (Dynamic/Fishman)
- Accumulated Precipitation (3/7/10/14-day rolling)

### Layer 2: Agronomic/Derived
- Leaf Wetness Duration (CART/SLD classifier)
- Leaf Wetness Estimation (RH/rainfall lookup)
- VPD (Tetens + rolling averages)
- Humidity Streak (consecutive days at RH thresholds)
- Phenological Gating (GDD-fraction trapezoidal membership)

### Layer 3: Disease/Pest Risk
- Fuzzy Mamdani (trapezoidal MFs, AND-aggregation, weighted defuzzification, gates)
- Rule-Based (boolean condition matching)
- Powdery Mildew Grape (UC IPM ascospore + conidial)

Disease models compose Layer 1 and Layer 2 outputs internally.

## 5. Threat Catalog

19 crops, 54 crop-threat pairings bundled as JSON seed data.
Each entry includes `bio_params`, `fuzzy_rules`, and `special_rules`.

Organism-specific special rules:
- Goidanich rule (Downy mildew): T>11C + RH>90% + rain>10mm
- Two-fifteens (Grey mold): 15C + 15h leaf wetness
- Mills table (Apple scab): temperature-dependent wetting periods
- Maryblyt (Fire blight): blossom blight risk model
- GDD flight windows (Codling moth): 250/468/900 GDD thresholds
- Wetness inhibition (Powdery mildew): free water inhibits infection

## 6. Weather Provider Contract

Standardized field names enforced by the ABC:
- `air_temperature` (C), `air_temperature_min` (C), `air_temperature_max` (C)
- `relative_humidity` (%), `dew_point` (C), `wind_speed` (km/h)
- `precipitation` (mm), `solar_radiation` (W/m2), `atmospheric_pressure` (hPa)

NOAA CDO is the shipped provider. Community providers subclass `WeatherProvider`.

## 7. GeoID Integration

AgStack Asset Registry GeoIDs (SHA-256 hex, 64 chars) resolve to coordinates via:
`GET https://api-ar.agstack.org/fetch-field-centroid/{geo_id}`

Raw lat/lon always works as fallback.

## 8. Service Layer

### REST API (FastAPI)
- `GET /api/v1/models` -- List models (filter by layer, crop)
- `GET /api/v1/models/{uuid}` -- Model metadata
- `POST /api/v1/calculate` -- Run a model
- `GET /api/v1/crops` -- Supported crops
- `GET /api/v1/crops/{crop}/threats` -- Threats for a crop
- `GET /health`, `GET /ready` -- Probes

### MCP Server (FastMCP)
Tools: `list_pest_models`, `get_model_info`, `get_supported_crops_tool`, `get_threats_for_crop_tool`, `explain_threat`
Resources: `pnd://models`, `pnd://crops`

### Database (PostgreSQL)
- `weather_cache` -- NOAA response cache (TTL-based)
- `model_runs` -- Calculation audit log
- `parcels` -- Registered fields for weather pre-fetching

## 9. CI/CD Pipeline

- `ci.yaml`: ruff lint/format, mypy strict, pytest, sphinx-build
- `release.yaml`: build wheel, publish PyPI, push Docker to GHCR
- `docs.yaml`: deploy Sphinx to GitHub Pages

## 10. FATFD Quality Process

Adapted from the Full Harvest platform harness:
- Phases F through 9 (Feedback -> Audit -> Test & Fix -> ... -> Learn -> Write State)
- Domain-specific guardrails (G-DATA, G-MODEL, G-API, G-COMMUNITY)
- Enforcement rules E1-E15
- Validator checks A-K
- `.audit/` directory with state, knowledge, manifest, and hooks

## 11. Community Extensibility

1. Subclass `PestModelBase`, implement `calculate()` and `validate_parameters()`
2. Assign a UUID, fill in `ModelMetadata`
3. Add entry point in `pyproject.toml`
4. Write tests against `WeatherDataFrame` fixtures
5. Publish to PyPI -- model auto-discovers in every deployment
