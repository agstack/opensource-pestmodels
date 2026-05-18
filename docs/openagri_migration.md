# OpenAgri Migration Guide

## For the OpenAgri Team, Contributors, and Community

This document explains how the OpenAgri Pest and Disease Management (PND) work has evolved into the AgStack `agstack-pnd` framework, why this evolution was necessary, what role the OpenAgri team plays going forward, and how the CI/CD process ensures that the OpenAgri team retains scientific authority over the models they created.

---

## This is an Evolution, Not a Replacement

The OpenAgri PND service -- built under the Horizon Europe OpenAgri project by Stefan Drobic (VizLore), Nikos Kalatzis (Green Supply Chain), Agrobit S.r.l., and collaborators -- is the scientific foundation of this framework. Nothing has been discarded. Everything has been preserved and elevated.

### What was built in OpenAgri

The OpenAgri team created:

1. **The Fuzzy Mamdani Risk Engine** -- A sophisticated disease/pest risk assessment system using trapezoidal membership functions, AND-aggregation, weighted defuzzification, and post-processing gates (streak penalty, Mills-type wetness gate, phenological scaling, lethal temperature cutoff). This is the most advanced open-source pest/disease risk engine in agriculture.

2. **54 Crop-Threat Definitions** -- Biological parameters for 19 crops and 35+ unique organisms, including base temperatures, lethal ranges, optimal ranges, phenological windows, humidity thresholds, and organism-specific special rules (Goidanich rule, two-fifteens rule, Mills table, Maryblyt model, GDD flight windows, wetness inhibition effects).

3. **The Leaf Wetness Estimation System** -- An RH/rainfall lookup-table model based on Pedro & Gillespie (1982) and Sentelhas et al. (2008) that estimates daily leaf wetness hours without requiring a dedicated leaf wetness sensor.

4. **The FastAPI Service Architecture** -- A production-grade deployment model with PostgreSQL, Alembic migrations, Docker Compose, and OpenMeteo weather integration.

5. **Pathogen-Specific Smoothing** -- The insight that fungal and bacterial pathogens (19 genera) respond to 7-day moving averages of temperature and humidity rather than daily values, while insects respond to daily conditions.

### What this framework adds

The `agstack-pnd` framework wraps all of the above in:

- **A composable three-layer architecture** that makes it possible for researchers worldwide to add new models that automatically compose with existing ones
- **A standardized weather provider interface** that decouples models from any specific weather API
- **A UUID-based model registry** with Python entry-point auto-discovery so anyone can publish models as pip packages
- **An MCP server** so AI agents can discover and query pest/disease models programmatically
- **A formal CI/CD quality process** (FATFD) that ensures every change is audited, tested, and reviewed before shipping
- **CODEOWNERS-based review authority** that gives the OpenAgri team veto power over changes to their domain

The OpenAgri work is not replaced -- it is the scientific core around which a broader community framework has been built.

---

## Where OpenAgri Code Lives in the New Framework

Every piece of OpenAgri work has a specific, traceable home:

| OpenAgri Component | New Location | Notes |
|-------------------|-------------|-------|
| Fuzzy Mamdani risk engine | `src/agstack_pnd/models/disease/fuzzy_mamdani.py` | Ported intact; trapezoidal MFs, AND-aggregation, defuzzification, all post-processing gates preserved |
| 54 crop-threat definitions | `src/agstack_pnd/catalog/data/pest_catalog.json` | All `bio_params`, `fuzzy_rules`, and `special_rules` preserved as structured JSON |
| Leaf wetness RH/rainfall lookup | `src/agstack_pnd/models/agronomic/leaf_wetness_rh.py` | Same thresholds (95%->20h, 85%->14h, 75%->8h, 65%->4h) and rainfall additive |
| VPD calculator | `src/agstack_pnd/models/agronomic/vpd.py` | Tetens formula with 3d/7d rolling averages |
| Humidity streak tracker | `src/agstack_pnd/models/agronomic/humidity_streak.py` | 6 RH threshold levels (60/70/75/80/85/90/95%) |
| Phenological gating | `src/agstack_pnd/models/agronomic/phenology.py` | GDD-fraction windowing with 12% soft-transition margin, BBCH stages |
| Pathogen genera smoothing | `src/agstack_pnd/models/disease/fuzzy_mamdani.py` | 19 genera detected by keyword matching, 7-day MA applied |
| GDD with multiple bases | `src/agstack_pnd/models/weather/growing_degree_days.py` | Multi-base support (0/5/10C + custom) |
| Rule-based risk engine | `src/agstack_pnd/models/disease/rule_based.py` | Boolean condition matching from upstream OpenAgri |
| Crop and ThreatModel schema | `src/agstack_pnd/foundation/types.py` | `ThreatDefinition`, `BioParams`, `FuzzyRule` as Pydantic models |

### What changed structurally (and why)

| Change | Reason |
|--------|--------|
| Extracted from monolithic FastAPI app into standalone library | Researchers can `pip install` and use models in notebooks without deploying a server |
| Models take `WeatherDataFrame` instead of fetching weather internally | Decouples computation from I/O; makes models testable and weather-provider-agnostic |
| Threat definitions are Pydantic models loaded from JSON | Validates schema automatically; makes it impossible to ship malformed biological parameters |
| Each model has a permanent UUID | Allows stable referencing across systems, publications, and API calls |
| Weather provider is an ABC, not hardcoded to OpenMeteo | NOAA shipped as default; community can add any provider without touching model code |
| Python entry-point auto-discovery | Third-party models install via pip and appear automatically -- no central registry bottleneck |

---

## OpenAgri Team's Role: Chief Maintainers and Scientific Authority

The OpenAgri team is not just acknowledged -- they are embedded into the governance and CI/CD process as the **scientific authority** for pest and disease modeling.

### CODEOWNERS: Formal Review Authority

The `.github/CODEOWNERS` file designates the `@agstack/openagri-maintainers` team as required reviewers for:

```
# Threat catalog and biological parameters
src/agstack_pnd/catalog/                    @agstack/openagri-maintainers

# Disease/pest risk models
src/agstack_pnd/models/disease/             @agstack/openagri-maintainers

# Fuzzy risk engine specifically
src/agstack_pnd/models/disease/fuzzy_mamdani.py   @agstack/openagri-maintainers

# Agronomic models
src/agstack_pnd/models/agronomic/           @agstack/openagri-maintainers

# Documentation
docs/                                       @agstack/openagri-maintainers
```

**What this means in practice**: No Pull Request that touches the threat catalog, biological parameters, disease models, agronomic models, or the fuzzy risk engine can be merged without approval from an OpenAgri maintainer. This is enforced by GitHub's branch protection rules -- it is not optional and cannot be bypassed.

### How the CI/CD Process Protects Scientific Integrity

Every contribution goes through four automated gates plus human review. Here is how each gate serves the OpenAgri team's interests:

```
Contributor opens a Pull Request
         |
         v
  +-------------------+
  | Gate 1: Lint       |  Ensures code quality and readability
  +-------------------+
         |
         v
  +-------------------+
  | Gate 2: Type Check |  Catches bugs in model interfaces
  +-------------------+
         |
         v
  +-------------------+
  | Gate 3: Tests      |  Verifies model outputs are correct
  |                   |  against known-good fixtures
  +-------------------+
         |
         v
  +-------------------+
  | Gate 4: Catalog &  |  Validates biological parameters,
  | FATFD Integrity    |  checks UUID uniqueness, runs the
  |                   |  FATFD quality harness
  +-------------------+
         |
         v
  +-------------------+
  | Human Review       |  OpenAgri maintainers must approve
  | (CODEOWNERS)       |  changes to their domain areas
  +-------------------+
         |
         v
  +-------------------+
  | Merge to master    |  Only after ALL gates pass AND
  |                   |  CODEOWNERS approve
  +-------------------+
```

**Gate 3 (Tests)** is particularly important: every model must have unit tests that verify outputs against known weather fixtures. If someone submits a change to the fuzzy risk engine or a threat definition, the tests will catch regressions in risk scores.

**Gate 4 (Catalog & FATFD Integrity)** validates:
- Every entry in `pest_catalog.json` has required fields (`scientific_name`, `common_name`, `crop`, `bio_params`)
- All model UUIDs are unique (no collisions)
- The FATFD harness passes all integrity checks
- Version numbers are consistent across `pyproject.toml` and `__init__.py`

### Domain Guardrails

The `.audit/GUARDRAILS.md` file encodes rules that protect the scientific domain:

- **G-MODEL-001**: Every disease model must cite its academic/institutional source
- **G-MODEL-002**: Model parameter changes require peer review from a domain expert
- **G-MODEL-003**: Threat catalog biological parameters must reference published literature
- **G-MODEL-004**: Model accuracy claims must be backed by validated test cases
- **G-COMMUNITY-001**: Community-contributed models must include tests and citations

These guardrails are **human-owned** -- the system may never modify them without explicit approval from the maintainers.

---

## How Community Contributions Flow Through the Process

Here is a concrete example of how a community researcher would contribute a new disease model and how the OpenAgri team maintains quality control:

### Example: A researcher wants to add an Apple Scab model

1. **Researcher forks the repo** and creates a branch `feature/apple-scab-model`

2. **Researcher creates the model** at `src/agstack_pnd/models/disease/apple_scab.py`:
   - Subclasses `PestModelBase`
   - Implements `calculate()` using Mills table infection periods
   - Adds academic citation to `ModelMetadata`
   - Assigns a UUID

3. **Researcher adds threat definition** to `pest_catalog.json`:
   - `bio_params` with temperature thresholds from published literature
   - `fuzzy_rules` for Mamdani engine compatibility
   - `special_rules` referencing the Mills/MacHardy model

4. **Researcher writes tests** in `tests/unit/test_apple_scab.py`:
   - Tests against synthetic weather fixtures
   - Verifies expected risk levels for known conditions

5. **Researcher opens a Pull Request**

6. **Automated gates run** (all must pass):
   - Lint: code is formatted correctly
   - Type check: interfaces are correct
   - Tests: new tests pass, no existing tests break
   - Catalog validation: `pest_catalog.json` schema is valid, UUIDs are unique

7. **CODEOWNERS review is triggered**:
   - Because the PR touches `src/agstack_pnd/models/disease/` and `src/agstack_pnd/catalog/`, GitHub automatically requests review from `@agstack/openagri-maintainers`
   - An OpenAgri maintainer reviews:
     - Are the biological parameters consistent with published literature?
     - Are the fuzzy rules reasonable for this organism?
     - Is the citation valid?
     - Do the test cases represent realistic weather conditions?

8. **OpenAgri maintainer approves** (or requests changes)

9. **PR is merged** -- the new model is available in the next release

### What the OpenAgri team can block

An OpenAgri maintainer can block a PR for any of these reasons:
- Biological parameters not supported by literature
- Fuzzy rules that produce unrealistic risk scores
- Missing or invalid academic citations
- Insufficient test coverage for edge cases
- Changes that regress existing model accuracy
- Threat definitions that conflict with established taxonomy

This is not a suggestion -- it is **mechanically enforced** by GitHub. The PR cannot be merged without their approval.

---

## Setting Up OpenAgri Maintainer Access

To activate the CODEOWNERS-based review process:

1. **Create a GitHub Team** called `openagri-maintainers` under the `agstack` org
2. **Add OpenAgri team members** to this team (Stefan Drobic, Nikos Kalatzis, other domain experts)
3. **Enable branch protection** on `master`:
   - Require pull request reviews before merging
   - Require review from CODEOWNERS
   - Require status checks to pass (lint, typecheck, test, catalog-validation)
   - Do not allow bypassing the above settings
4. **Grant the team write access** to this repository

Once this is configured, no changes to the disease models, threat catalog, or biological parameters can land without OpenAgri approval.

---

## Migrating Existing OpenAgri Deployments

If you currently run the OpenAgri PND FastAPI service (`openagri-eu/OpenAgri-PestAndDiseaseManagement`), here is how to transition:

### Option 1: Use agstack-pnd as a library alongside your existing service

```python
# In your existing FastAPI app, add agstack-pnd as a dependency
# and call models directly

from agstack_pnd.models.disease.fuzzy_mamdani import FuzzyMamdaniRisk
from agstack_pnd.catalog.loader import get_threat

threat = get_threat("grape", "Plasmopora viticola")
model = FuzzyMamdaniRisk()
result = model.calculate(weather_data_from_your_system, threat=threat)
```

Your existing weather pipeline, database, and API stay intact. You just use `agstack-pnd` models for computation.

### Option 2: Deploy the agstack-pnd server as a replacement

```bash
docker compose -f docker/compose.yaml up -d
```

The agstack-pnd server provides the same capabilities (GDD, risk assessment, crop/threat management) with added MCP support and the full model registry.

### Option 3: Gradual migration

1. Deploy agstack-pnd alongside your existing service
2. Route new API consumers to agstack-pnd
3. Verify output parity on shared threat definitions
4. Gradually decommission the old service

### Data migration

The threat catalog in `pest_catalog.json` was ported directly from the OpenAgri `data/pest.json`. If you have added custom threat definitions in your database, you can:
1. Export them as JSON matching the `pest_catalog.json` schema
2. Add them to the catalog file
3. Open a PR (OpenAgri maintainers review and merge)

---

## Frequently Asked Questions

### Q: Is the OpenAgri PND service being shut down?

No. The existing OpenAgri PND service continues to operate independently. The `agstack-pnd` framework is a downstream evolution that packages the same scientific models in a more composable, extensible architecture. Both can coexist.

### Q: Will changes to agstack-pnd flow back to OpenAgri?

The projects are Apache-2.0 licensed. Any improvements made in `agstack-pnd` (bug fixes, new threat definitions, model refinements) are freely available to the OpenAgri project. The OpenAgri team can cherry-pick changes back into their service at any time.

### Q: Who decides what biological parameters are correct?

The OpenAgri maintainers, through the CODEOWNERS review process. No change to biological parameters (`pest_catalog.json`), fuzzy rules, or disease model logic can be merged without their approval. This is enforced by GitHub's branch protection -- it is not a social contract, it is a technical gate.

### Q: Can the community override OpenAgri's review decisions?

No. CODEOWNERS review is mandatory for the designated code paths. If the OpenAgri team rejects a PR, it cannot be merged regardless of how many other approvals it has. This is by design -- domain expertise must gatekeep scientific accuracy.

### Q: What if an OpenAgri maintainer is unavailable?

The `@agstack/openagri-maintainers` team should have multiple members so that review is not blocked by any single person's availability. The AgStack TSC (Technical Steering Committee) can add or remove members from the team as needed.

### Q: How are new crops and threats added?

1. Open a PR adding the threat definition to `pest_catalog.json`
2. Include `bio_params` and `fuzzy_rules` with literature references
3. Add test cases verifying expected risk outputs
4. OpenAgri maintainers review the biological parameters
5. Once approved and all CI gates pass, the PR is merged
6. The new threat is available in the next release

### Q: What happens to the OpenAgri Horizon Europe funding acknowledgment?

The `CHANGELOG.md`, `README.md`, `docs/executive_summary.md`, and every model file that ports OpenAgri code includes explicit attribution. The Fuzzy Mamdani engine cites "OpenAgri-EU PND fuzzy risk system; Agrobit S.r.l." in its `ModelMetadata.citation` field, which propagates to auto-generated documentation and API responses.

---

## Summary

| Aspect | OpenAgri PND Service | agstack-pnd Framework |
|--------|--------------------|-----------------------|
| **Scientific models** | Created here | Ported and preserved here |
| **Threat catalog** | 54 crop-threat pairings | Same 54 pairings, structured as validated JSON |
| **Fuzzy risk engine** | Implemented here | Ported intact with all gates and smoothing |
| **Architecture** | Monolithic FastAPI + Postgres | Three-layer composable library + optional server |
| **Weather source** | OpenMeteo (hardcoded) | Pluggable (NOAA shipped, any provider addable) |
| **Model discovery** | Database-driven | UUID registry + Python entry-point auto-discovery |
| **AI integration** | None | MCP server (Model Context Protocol) |
| **Quality process** | Manual | FATFD harness + 4 CI gates + CODEOWNERS review |
| **OpenAgri team role** | Creators | Chief maintainers with formal veto authority |
| **License** | EUPL-1.2 / Apache-2.0 | Apache-2.0 |
| **Governance** | OpenAgri consortium | AgStack Foundation (Linux Foundation) with OpenAgri maintainer authority |

The message is simple: **the OpenAgri team built the science, and this framework ensures that science reaches the widest possible audience while the OpenAgri team retains control over its integrity.**
