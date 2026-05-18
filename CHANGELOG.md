# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0a1] - 2026-05-17

### Added
- Complete architectural redesign as hierarchical pest/disease modeling framework
- Three-layer model hierarchy: Weather -> Agronomic -> Disease
- `PestModelBase` ABC with UUID-based model registry and entry-point discovery
- `WeatherProvider` ABC with standardized field names
- NOAA Climate Data Online weather provider
- GeoID resolver for AgStack Asset Registry integration
- Threat catalog: 19 crops, 54 crop-threat pairings from OpenAgri
- Layer 1 models: GDD (multi-base), Chill Hours (Utah + 32-45), Chill Portions, Accumulated Precipitation
- Layer 2 models: Leaf Wetness (CART + RH lookup), VPD, Humidity Streak, Phenological Gating
- Layer 3 models: Fuzzy Mamdani risk engine, Rule-based risk, Powdery Mildew Grape (UC IPM)
- FastAPI REST API with model discovery, calculation, and caching
- MCP server (Model Context Protocol) for AI agent integration
- PostgreSQL backend for weather caching and model run audit
- Docker Compose deployment
- Sphinx auto-generated documentation
- FATFD quality harness
- GitHub Actions CI/CD (lint, test, typecheck, release, docs)

### Changed
- Package renamed from `agralogics` to `agstack-pnd`
- License changed from GPL-3.0 to Apache-2.0
- Build system migrated from `setup.py` to `pyproject.toml`
- Weather provider decoupled from proprietary Agralogics API

### Removed
- Legacy `agralogics` package structure
- Hard dependency on Agralogics Weather Server API
