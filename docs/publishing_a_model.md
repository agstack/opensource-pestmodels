# Publishing a model to agstack-pnd

This guide is for scientists who have a pest or disease model and want it to run
inside the AgStack Digital Public Infrastructure (DPI) — discoverable by anyone,
runnable over an API and by AI agents, fed by governed weather data, and able to
publish its results back into the shared data plane.

You do **not** fork this repository. You publish a small pip package; the runtime
finds your model automatically. A complete, working example lives in
[`examples/model-template/`](../examples/model-template/).

## The mental model

```
        you write this                      the DPI runtime provides this
   ┌─────────────────────┐        ┌──────────────────────────────────────────┐
   │  PestModelBase       │        │ GeoID resolution (AR2)                    │
   │   .calculate(wx) ->  │  <───  │ weather as BITEs (Pancake/TerraPipe)      │
   │      ModelResult     │        │ REST /calculate + MCP run_forecast        │
   └─────────────────────┘        │ result published as a PEST_DISEASE BITE   │
                                    └──────────────────────────────────────────┘
```

Your model is **pure computation**: weather in, risk out. Everything else —
identity, consent, data fetching, transport, aggregation — is the platform's job.

## Step 1: Write the model

Subclass `PestModelBase` and implement `validate_parameters` and `calculate`.

```python
from typing import ClassVar
from uuid import UUID
from agstack_pnd.foundation.base_model import PestModelBase
from agstack_pnd.foundation.types import (
    DailyScore, ModelLayer, ModelMetadata, ModelResult, WeatherDataFrame,
)

class MyModel(PestModelBase):
    metadata: ClassVar[ModelMetadata] = ModelMetadata(
        uuid=UUID("<uuid4-you-generate-once>"),
        name="my_model",
        display_name="My Model",
        version="0.1.0",
        layer=ModelLayer.WEATHER,          # or PEST / DISEASE
        description="What it does, in one sentence.",
        required_weather_fields=["air_temperature", "relative_humidity"],
        citation="Author et al. (Year). Journal.",
        author="Your Lab",
    )

    def validate_parameters(self, parameters): ...
    def calculate(self, weather_data, parameters=None, threat=None) -> ModelResult: ...
```

Rules that keep the DPI trustworthy:

- **Stable identity.** Generate `metadata.uuid` once (`python -c "import uuid; print(uuid.uuid4())"`)
  and never change it. Bump `version` when the science changes.
- **Declare inputs.** Everything you read must be in `required_weather_fields`
  so the runtime fetches exactly those fields. Supported names include
  `air_temperature`, `air_temperature_min/max`, `relative_humidity`,
  `precipitation`, `wind_speed`, `dew_point`.
- **No side effects.** Do not call the network or read files in `calculate`.

## Step 2: Declare the entry point

In your `pyproject.toml`:

```toml
[project.entry-points."agstack_pnd.models"]
my_model = "my_package.my_module:MyModel"
```

That single table is the entire integration contract. On install, agstack-pnd's
`ModelRegistry` discovers your class through this entry point.

## Step 3: Test it (no platform needed)

Build a `WeatherDataFrame` from numpy arrays and assert on the `ModelResult`.
See [`examples/model-template/tests/`](../examples/model-template/tests/).

```bash
pip install -e .
pytest
```

## Step 4: Run it through the DPI

Install your wheel alongside agstack-pnd and start the server (or use the
[`dpi-demo`](https://github.com/agstack/pancake/tree/main/dpi-demo) stack). Then:

```bash
# REST
curl -X POST localhost:8080/api/v1/calculate -H 'content-type: application/json' -d '{
  "model_uuid": "<your-uuid>", "geo_id": "<geoid>",
  "start_date": "2026-07-01", "end_date": "2026-07-14",
  "weather_provider": "dpi", "publish": true
}'
```

- `weather_provider: "dpi"` makes the runtime read weather **BITEs** (ingested
  from TerraPipe by Pancake's TAP worker) keyed by your field's GeoID — you never
  touch a weather API.
- `field_grant` (an AR2 SD-JWT credential) authorizes access to a private field's
  exact geometry and, when enabled, its grant-gated weather.
- `publish: true` writes your result back as a `PEST_DISEASE` BITE, so other
  services can join your risk to soil/satellite/insurance data on the GeoID, and
  the district-level [`/aggregate`](../src/agstack_pnd/server/routers/aggregate.py)
  endpoint can roll it into population statistics.

AI agents get the same capability through the MCP `run_forecast` tool.

## Step 5: Publish

Publish the wheel to PyPI (or a private index) and share the package name. Anyone
who `pip install`s it gets your model registered in their agstack-pnd instance.

## What "good" looks like

- Deterministic: same inputs → same `ModelResult`.
- Documented: real `citation`, `author`, and a clear `description`.
- Honest metadata: `required_weather_fields` matches what you actually read.
- Tested: unit tests that a reviewer can run in seconds.
