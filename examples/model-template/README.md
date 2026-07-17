# agstack-pnd model template

A complete, minimal example of a **third-party pest/disease model** that plugs
into `agstack-pnd` with **no fork and no PR to the core repo**. You publish an
ordinary pip wheel; the runtime auto-discovers it via a Python entry point.

## Layout

```
model-template/
  pyproject.toml                 # declares the agstack_pnd.models entry point
  src/my_pnd_model/
    __init__.py
    heat_stress.py               # your model: a PestModelBase subclass
  tests/test_heat_stress.py      # pure-computation unit tests
```

## The one line that matters

```toml
[project.entry-points."agstack_pnd.models"]
heat_stress_index = "my_pnd_model.heat_stress:HeatStressIndex"
```

When your package is installed, `agstack-pnd`'s `ModelRegistry` finds this entry
point and serves your model over the REST API and MCP tools automatically.

## Try it

```bash
pip install -e .            # from this directory (installs agstack-pnd too)
pytest                      # run the model's unit tests

# confirm the runtime discovered it:
python -c "from agstack_pnd.foundation.model_registry import ModelRegistry as R; \
           print([m.name for m in R().list_models()])"
```

Then run it through the DPI like any built-in model:

```bash
curl -X POST localhost:8080/api/v1/calculate -H 'content-type: application/json' -d '{
  "model_uuid": "f0000000-1111-4222-8333-444444444444",
  "geo_id": "<your-geoid>",
  "start_date": "2026-07-01",
  "end_date": "2026-07-14",
  "weather_provider": "dpi"
}'
```

## Rules of the road

1. **A model is pure computation.** It receives a `WeatherDataFrame` and returns
   a `ModelResult`. It must not fetch weather, resolve GeoIDs, or hit the network
   — the runtime does all of that and hands you clean, aligned arrays.
2. **Stable identity.** Mint a `uuid4` once for `metadata.uuid` and never change
   it; it is your model's identity across the whole DPI. Bump `version` when the
   science changes; only mint a new uuid for a genuinely different model.
3. **Declare your inputs.** List every field you read in
   `metadata.required_weather_fields`; the runtime fetches exactly those.
4. **Cite your work.** Fill in `citation` and `author` — published models are
   meant to be discoverable and creditable.

See [`docs/publishing_a_model.md`](../../docs/publishing_a_model.md) for the full
walkthrough, including how weather reaches your model as BITEs and how results are
published back to the DPI.
