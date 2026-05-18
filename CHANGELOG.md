# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0a1] - 2026-05-18

### Added
- Complete architectural redesign as hierarchical pest/disease modeling framework
- Three-layer model hierarchy: Weather -> Agronomic -> Disease
- `PestModelBase` ABC with UUID-based model registry and entry-point discovery
- `WeatherProvider` ABC with standardized field names
- NOAA Climate Data Online weather provider
- GeoID resolver for AgStack Asset Registry integration
- Threat catalog: 19 crops, 54 crop-threat pairings ported from OpenAgri (8 seeded, expanding)
- Layer 1 models: GDD (multi-base), Chill Hours (Utah + 32-45), Chill Portions, Accumulated Precipitation
- Layer 2 models: Leaf Wetness (CART + RH lookup), VPD, Humidity Streak, Phenological Gating
- Layer 3 models: Fuzzy Mamdani risk engine, Rule-based risk, Powdery Mildew Grape (UC IPM)
- FastAPI REST API with model discovery, calculation endpoints, crop/threat catalog
- MCP server (Model Context Protocol) mounted at `/mcp` for AI agent integration
- PostgreSQL backend for weather caching and model run audit
- Docker Compose deployment (Dockerfile, compose.yaml, entrypoint.sh)
- Sphinx auto-generated documentation
- FATFD quality harness (.audit/ directory with state, knowledge, guardrails, validator)
- GitHub Actions CI/CD: 4 quality gates (lint, typecheck, tests, catalog/FATFD integrity)
- GitHub Actions release pipeline (PyPI wheel, GHCR Docker image, GitHub Pages docs)
- CODEOWNERS: OpenAgri maintainers as required reviewers for disease models and threat catalog
- 18 passing unit tests with synthetic weather fixtures
- Documentation suite:
  - User Manual (library, REST API, and MCP usage with code examples)
  - MCP Server Guide (installation, agent configuration, tool/resource reference)
  - Executive Summary (vision, stakeholders, coverage, community strategy)
  - Design Architecture (three-layer hierarchy, ABCs, CI/CD, FATFD)
  - OpenAgri Migration Guide (evolution narrative, maintainer roles, CI/CD governance)
  - Contributor Guide (adding models, threats, providers, PR process, CODEOWNERS)
  - Deployment Guide (Docker, pip, environment variables)

### Changed
- Package renamed from `agralogics` to `agstack-pnd`
- License changed from GPL-3.0 to Apache-2.0
- Build system migrated from `setup.py` to `pyproject.toml`
- Weather provider decoupled from proprietary Agralogics API
- Repository description and topics updated on GitHub

### Removed
- Legacy `agralogics` package structure
- Hard dependency on Agralogics Weather Server API

### Acknowledgments
- OpenAgri (Horizon Europe): Fuzzy Mamdani engine, threat catalog, leaf wetness estimation.
  Stefan Drobic (VizLore), Nikos Kalatzis (Green Supply Chain), Agrobit S.r.l.
- agstack/pest-models: Original GDD, chill, leaf wetness, powdery mildew models
