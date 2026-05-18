# Executive Summary: AgStack Pest & Disease Models

## Problem Statement

Pest and disease models exist scattered across academic papers, proprietary platforms, and siloed government tools. No open, standardized, composable framework exists for researchers, extension agents, or agtech companies to build on. This fragmentation means:

- **Researchers** publish models in papers that are rarely implemented as usable software
- **Agtech companies** each build their own proprietary model stacks, duplicating effort
- **Extension agents** lack tools to translate field conditions into actionable disease risk
- **AI systems** cannot access pest/disease knowledge through standardized protocols

## Vision

**agstack-pnd** is the standard open-source platform for hierarchical pest and disease modeling, hosted under the Linux Foundation's AgStack project. It provides:

1. A **composable three-layer architecture** (Weather -> Agronomic -> Disease) where models build on each other
2. A **plug-and-play weather interface** where any data provider can be swapped in (NOAA shipped as default)
3. A **UUID-based model registry** where anyone can publish models as pip packages that auto-discover
4. A **full-service deployment** (REST API + MCP server + PostgreSQL) downloadable by anyone
5. An **MCP server** so AI agents can autonomously query pest/disease risk

## Stakeholder Value

| Stakeholder | Value Proposition |
|-------------|-------------------|
| **Researchers** | Publish models as pip-installable packages. Automatic discovery, documentation, and citation tracking. No infrastructure needed. |
| **Agtech companies** | One API (REST or MCP) to access any pest/disease model. Standardized weather field names. UUID-stable model references. |
| **Extension agents** | GeoID-based queries: give a field ID, crop, and date range -- get disease risk with plain-language explanations. |
| **AI agents** | MCP protocol integration. Any LLM-based agricultural advisor can discover and query models programmatically. |
| **Open-source community** | Entry-point model registration. Contributor templates. FATFD quality process ensures every contribution is audited and tested. |

## Coverage at Launch

- **19 crops**: Almond, Apple, Apricot, Avocado, Banana, Cherry, Citrus, Cocoa, Coffee, Grape, Guava, Hazelnut, Mango, Olive, Papaya, Peach, Pear, Pistachio, Plum
- **54 crop-threat pairings**: 21 unique diseases (fungi, bacteria, oomycetes) and 19 unique pests (insects, mites)
- **13 registered models** across three layers
- **NOAA Climate Data Online** as the shipped weather provider (pluggable interface for community additions)

## Architecture Summary

```
Layer 1 (Weather)     : GDD, Chill Hours/Portions, Accumulated Precipitation
Layer 2 (Agronomic)   : Leaf Wetness (CART + RH), VPD, Humidity Streak, Phenology
Layer 3 (Disease/Pest): Fuzzy Mamdani Risk, Rule-Based Risk, Powdery Mildew Grape (UC IPM)
```

Disease models compose lower-layer outputs. The Fuzzy Mamdani engine operates on ANY crop-threat pairing via parameterized ThreatDefinitions, not hardcoded logic per organism.

## Relationship to Existing Work

This project absorbs and supersedes three legacy AgStack repositories:

| Repository | What we took | What we improved |
|-----------|-------------|-----------------|
| `agstack/pest-models` | GDD, Chill, Leaf Wetness, Powdery Mildew math | Decoupled from proprietary Agralogics API; added UUIDs, types, tests |
| `agstack/OpenAgri-PestAndDiseaseManagement` | Rule-based risk engine, GDD intervals | Extracted from monolithic service; made composable |
| `openagri-eu/OpenAgri-PestAndDiseaseManagement` | Fuzzy Mamdani engine, 54 threat definitions, leaf wetness lookup tables | Ported into clean ABC framework; standardized field names |

## Community Strategy

- **Entry-point model registration**: `pip install agstack-pnd-my-model` auto-registers
- **Contributor guide**: Step-by-step instructions for adding models, providers, or threats
- **FATFD quality process**: Every change is audited, tested, and documented before shipping
- **Apache-2.0 license**: Maximum permissiveness for commercial and academic adoption

## Linux Foundation / AgStack Alignment

- **GeoID integration**: Native support for AgStack Asset Registry field identifiers
- **Open governance**: All development public on GitHub under the agstack org
- **Standard interfaces**: WeatherProvider ABC, PestModelBase ABC, and ThreatDefinition schema as community contracts
- **Interoperability**: JSON-LD response support for OpenAgri ecosystem compatibility
