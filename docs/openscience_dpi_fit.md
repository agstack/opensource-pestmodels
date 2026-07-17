# agstack-pnd as an OpenScience DPI Service

**Status:** design note · **Audience:** contributors and maintainers.

This note explains how `agstack-pnd` fits into the AgStack Digital Public Infrastructure (DPI) as an open, GeoID-addressable pest-and-disease service, and what we plan to change to make that fit clean. It is a contributor-facing companion to the fuller architecture; see also [design_architecture.md](design_architecture.md) and [executive_summary.md](executive_summary.md).

---

## 1. The idea in one paragraph

AgStack's foundation gives every field a **GeoID** — a stable name computed from its boundary, so anyone can derive the same id from the same field without a central registry. `agstack-pnd` already resolves a GeoID to a location and runs three-layer models (weather → agronomic → disease/pest risk). The OpenScience direction is to make our **outputs first-class DPI artifacts**: keyed on the GeoID, mergeable with other providers' data for the same field, aggregatable across many fields, and open to citizen-science feedback that improves the models over time.

---

## 2. Why field identity matters for pest & disease

A single farmer asking "what's the risk on my field today?" barely needs identity — the answer is mostly a function of local weather. Identity becomes essential the moment we do the things that make PnD *science*:

- **Aggregate statistics.** "What % of maize fields in this district show high fall-armyworm risk this week?" is a ratio over **distinct** fields. If the same field was captured three times and counted three times, the percentage is wrong. Stable, de-duplicated identity makes the denominator correct.
- **Hierarchical roll-ups.** Risk rolls up plot → farm → co-op → region. AgStack records a small plot nested inside a larger field as a *child-of* relationship (not a merge), so a region-level statistic is a clean tree walk instead of a double-count.
- **The learning loop.** Predict risk → a scout or citizen reports the actual outbreak → the model is calibrated. This only works if every observation attaches to **one durable identity per field**, across time and across reporters.
- **Cross-provider merges.** When our risk output and someone else's soil or satellite data both key on the **same GeoID**, a consumer merges them with a simple join instead of fuzzy geometry matching.

Short version: identity is *convenience* for one field today, and *correctness* for aggregation, attribution, and learning — which is exactly the OpenScience value.

---

## 3. What we plan to change in `agstack-pnd`

| # | Change | Where |
|---|---|---|
| A | **GeoID-first results** — every risk output carries the canonical `geo_id` as its primary key, not just lat/lon. | `foundation/types.py`, `models/*`, response models in `server/app.py` |
| B | **Grant-aware access** — accept/forward an AgStack access grant; use the coarse (masked) centroid by default and the exact boundary only when a grant is presented (e.g., sub-field zoning). | `foundation/geo_resolver.py` (add auth header + optional `fetch-field-wkt`), `server/config.py` |
| C | **DPI weather provider** — a provider that pulls weather through the DPI data path (GeoID + owner grant), alongside the existing NOAA provider. | new `providers/dpi_weather.py`, `foundation/weather_provider.py` |
| D | **Publishable results** — emit risk as signed, GeoID-addressed artifacts so they can be consumed (and revoked) in the DPI data plane. | new publish path in `server/` |
| E | **Aggregation endpoint** — `POST /aggregate` over a set of GeoIDs (or a parent GeoID) that walks child-of links and returns **distinct-field** statistics. | `server/app.py`, `server/mcp_server.py` |
| F | **Citizen-science intake** — attach an observation (outbreak yes/no, severity) to a GeoID to feed the learning loop. | `server/app.py` |
| G | **Provenance metadata** — every output records model id + version, catalog version, weather source, timestamp, and the field-identity regime it assumed. | `foundation/types.py`, `catalog/loader.py` |

### Note on identity "regime"

A GeoID is unique per field **relative to a fixed set of covering parameters and canonicalization rules** (the "regime"). Two captures of the same field normally produce the **same** GeoID; when they differ slightly, the Asset Registry resolves them to one canonical GeoID at registration. But a *different* identity system (e.g., FAO's) will name the same field differently — resolvable to the same location, not equal. That is why change G records the regime: so a downstream consumer knows whether two GeoIDs are directly comparable.

---

## 4. What we ask of the DPI foundation

So the fit is clean from both sides, `agstack-pnd` depends on the foundation to:

1. **Name PnD as a Layer-3 service** in the DPI architecture (a replaceable reference implementation of an open interface).
2. **Specify an aggregation contract** — how a service walks child-of links and reports distinct-field statistics using only the coarse (L0) view, without needing exact geometry.
3. **Carry pest-relevant weather inputs** (leaf wetness, humidity, min/max temperature windows) through the shared weather interface, not just the fields a weather widget needs.
4. **Publish the covering regime** (identity parameters + default resolution threshold) as a shared artifact any service can read.

---

## 5. Boundaries

- `agstack-pnd` is a **Layer-3 service**: it *consumes* the foundation (GeoID, grant, node) and must never become something the foundation depends on. Any of our components can be swapped for another implementation of the same interface.
- Our OpenScience obligations (auditing, citizen-science intake) align with the CIAT OpenScience program.
- We publish results into the DPI data plane; we do not become a required data plane for anyone else.

---

## 6. See also

- [design_architecture.md](design_architecture.md) — three-layer model, GeoID integration, service layer.
- [executive_summary.md](executive_summary.md) — problem, vision, stakeholder value.
- [mcp_server_guide.md](mcp_server_guide.md) — how models are exposed to AI agents over MCP.
- [openagri_migration.md](openagri_migration.md) — how OpenAgri's PnD work evolved into this framework.
