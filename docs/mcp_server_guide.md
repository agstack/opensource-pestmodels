# MCP Server Guide

## What is MCP?

The **Model Context Protocol (MCP)** is an open standard created by Anthropic that allows AI agents (Claude, GPT, open-source LLMs, custom agents) to discover and use external tools and data sources. Think of it as a universal plug-and-play protocol between AI assistants and software systems.

The `agstack-pnd` MCP server exposes every pest and disease model, the full threat catalog, and crop information as **tools** and **resources** that any MCP-compatible AI agent can call. This means an agricultural advisor chatbot, a farm management AI, or a research assistant can autonomously query disease risk for any supported crop and location.

---

## Quick Start

### Option A: Run with the full server (recommended)

```bash
# Install with server dependencies
pip install "agstack-pnd[server]"

# Set your NOAA token for weather data
export PND_NOAA_API_TOKEN=your-noaa-cdo-token

# Start the server (REST API + MCP on same port)
uvicorn agstack_pnd.server.app:create_app --factory --host 0.0.0.0 --port 8000
```

The MCP server is now available at `http://localhost:8000/mcp`.
The REST API is at `http://localhost:8000/api/v1/`.
The OpenAPI docs are at `http://localhost:8000/docs`.

### Option B: Run with Docker Compose

```bash
cd docker
cp .env.example .env
# Edit .env with your NOAA API token
docker compose up -d
```

MCP server at `http://localhost:8000/mcp`.

### Option C: Run the MCP server standalone (stdio transport)

If you only want the MCP server without the REST API (e.g., for local AI tools that spawn MCP servers as subprocesses):

```bash
pip install "agstack-pnd[server]"
python -m agstack_pnd.server.mcp_server
```

This runs the MCP server over **stdio** (stdin/stdout), which is the standard transport for local MCP connections from tools like Claude Desktop, Cursor, and other MCP clients.

---

## Connecting Your AI Agent

### Claude Desktop

Add to your Claude Desktop MCP configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

**For HTTP transport (server running):**

```json
{
  "mcpServers": {
    "agstack-pnd": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

**For stdio transport (Claude spawns the server):**

```json
{
  "mcpServers": {
    "agstack-pnd": {
      "command": "python",
      "args": ["-m", "agstack_pnd.server.mcp_server"],
      "env": {
        "PND_NOAA_API_TOKEN": "your-noaa-token"
      }
    }
  }
}
```

### Cursor IDE

Add to your Cursor MCP settings (`.cursor/mcp.json` in your project or global settings):

```json
{
  "mcpServers": {
    "agstack-pnd": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

Or for stdio:

```json
{
  "mcpServers": {
    "agstack-pnd": {
      "command": "python",
      "args": ["-m", "agstack_pnd.server.mcp_server"]
    }
  }
}
```

### Any MCP-compatible client

The server supports **Streamable HTTP** transport at the `/mcp` endpoint. Any client that implements the MCP specification can connect by pointing to:

```
http://<host>:8000/mcp
```

The server responds to standard MCP JSON-RPC messages: `tools/list`, `tools/call`, `resources/list`, `resources/read`.

### Python client (programmatic)

```python
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def query_pnd():
    async with streamablehttp_client("http://localhost:8000/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            for tool in tools.tools:
                print(f"Tool: {tool.name} -- {tool.description}")

            # Call a tool
            result = await session.call_tool(
                "get_supported_crops_tool",
                arguments={},
            )
            print(result.content)
```

---

## Available Tools

These are the functions your AI agent can call:

### `list_pest_models`

List all available pest and disease models. Optionally filter by layer or crop.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `layer` | string | No | Filter: `"weather"`, `"agronomic"`, or `"disease"` |
| `crop` | string | No | Filter by crop name (e.g., `"grape"`, `"apple"`) |

**Returns:** Array of model metadata objects with UUID, name, description, layer, supported crops, and required weather fields.

**Example agent interaction:**
> Agent: "What disease models are available for grapes?"
> Calls: `list_pest_models(layer="disease", crop="grape")`
> Returns: Fuzzy Mamdani Risk, Rule-Based Risk, Powdery Mildew Grape (UC IPM)

### `get_model_info`

Get detailed metadata and parameter schema for a specific model.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `model_uuid` | string | Yes | The model's UUID |

**Returns:** Full model metadata including version, citations, required weather fields, dependencies, and parameter schema.

**Example agent interaction:**
> Agent: "Tell me about the Fuzzy Mamdani risk engine"
> Calls: `get_model_info(model_uuid="a1b2c3d4-0004-4000-8000-000000000001")`

### `get_supported_crops_tool`

List all crops that have at least one pest/disease model available.

**Parameters:** None

**Returns:** Array of crop name strings.

**Example agent interaction:**
> Agent: "What crops can I assess for disease risk?"
> Calls: `get_supported_crops_tool()`
> Returns: `["apple", "coffee", "grape", "olive", "pear", ...]`

### `get_threats_for_crop_tool`

List all pest and disease threats for a specific crop.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `crop` | string | Yes | Crop name (e.g., `"grape"`) |

**Returns:** Array of objects with scientific name, common name, and threat type.

**Example agent interaction:**
> Agent: "What threatens my grape vineyard?"
> Calls: `get_threats_for_crop_tool(crop="grape")`
> Returns: Downy mildew, Powdery mildew, Grey mold, Phomopsis, Black rot

### `explain_threat`

Get detailed biological parameters for a specific crop-threat pairing.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `crop` | string | Yes | Crop name |
| `scientific_name` | string | Yes | Scientific name of the organism |

**Returns:** Full threat definition including biological parameters (temperatures, streaks, phenology windows), fuzzy rules, and any special rules.

**Example agent interaction:**
> Agent: "What conditions favor grey mold on grapes?"
> Calls: `explain_threat(crop="grape", scientific_name="Botrytis cinerea")`
> Returns: Optimal 15-25C, needs 15h wetness ("two-fifteens rule"), high risk when RH > 90% with rainfall

---

## Available Resources

MCP resources are read-only data that agents can load for context:

### `pnd://models`

Full catalog of all registered pest/disease models in markdown format. Contains UUID, layer, supported crops, and description for every model.

**Use case:** Agent loads this resource at the start of a conversation to understand what models are available.

### `pnd://crops`

List of all supported crops with their threat counts.

**Use case:** Agent loads this for a quick overview of coverage.

---

## Example Conversations

### Conversation 1: Farm advisor assessing disease risk

```
User: "I have a grape vineyard near Napa Valley. What diseases should I
       worry about in June?"

Agent thinking:
  1. Call get_threats_for_crop_tool(crop="grape")
     -> Downy mildew, Powdery mildew, Grey mold, Phomopsis, Black rot

  2. Call explain_threat(crop="grape", scientific_name="Plasmopora viticola")
     -> Optimal 18-25C, needs rain >10mm, Goidanich rule applies

  3. Call explain_threat(crop="grape", scientific_name="Uncinula necator")
     -> Optimal 20-28C, DRY conditions favor it (wetness inhibitory)

Agent response: "For your Napa vineyard in June, watch for:
  - Powdery mildew (highest risk in warm, dry weather 20-28C)
  - Downy mildew (if you get rain events >10mm with RH >90%)
  - Grey mold (later in season, needs 15C + 15 hours leaf wetness)
  
  Note that powdery mildew is unusual -- free water actually inhibits
  it, unlike most fungal diseases. Your dry June weather increases
  powdery mildew risk while reducing downy mildew risk."
```

### Conversation 2: Researcher exploring model capabilities

```
User: "What weather models does agstack-pnd offer?"

Agent thinking:
  1. Call list_pest_models(layer="weather")
     -> GDD, Chill Hours Utah, Chill Hours 32-45, Chill Portions, Accumulated Precip

Agent response: "There are 5 weather/accumulation models available:
  1. Growing Degree Days (multi-base: configurable base temperature)
  2. Chill Hours - Utah Model (with negative weighting above 60F)
  3. Chill Hours - 32-45F Model (simple binary accumulation)
  4. Chill Portions - Dynamic Model (Fishman biochemical model)
  5. Accumulated Precipitation (rolling 3/7/10/14-day windows)"
```

### Conversation 3: Extension agent checking fire blight risk

```
User: "Is my pear orchard at risk for fire blight? It's been warm and
       humid this week."

Agent thinking:
  1. Call explain_threat(crop="pear", scientific_name="Erwinia amylovora")
     -> Base temp 12.7C, optimal 24-29C, needs RH >85%, phenology
        window BBCH 57-69 (bloom), references Maryblyt/Cougarblight model

Agent response: "Fire blight risk depends on several factors:
  - It's driven by the bacterium Erwinia amylovora
  - Highest risk during bloom (BBCH stages 57-69)
  - Critical conditions: 24-29C with RH above 85% and any rainfall
  - The Maryblyt model uses accumulated degree-days (base 12.7C)
  
  If your orchard is currently in bloom AND temperatures are 24-29C
  with high humidity, risk is elevated. Are your trees in bloom?"
```

---

## Architecture: How the MCP Server Works

```
AI Agent (Claude, GPT, Cursor, custom)
    |
    | MCP JSON-RPC over Streamable HTTP (or stdio)
    v
+--------------------------------------------------+
|  FastMCP Server (mounted at /mcp)                |
|                                                  |
|  Tools:                                          |
|    list_pest_models  ->  ModelRegistry           |
|    get_model_info    ->  ModelRegistry           |
|    get_supported_crops_tool -> Catalog            |
|    get_threats_for_crop_tool -> Catalog           |
|    explain_threat    ->  Catalog                 |
|                                                  |
|  Resources:                                      |
|    pnd://models      ->  ModelRegistry (markdown) |
|    pnd://crops       ->  Catalog (markdown)      |
+--------------------------------------------------+
    |
    | (shares process with)
    v
+--------------------------------------------------+
|  FastAPI REST API (on same port)                 |
|                                                  |
|  /api/v1/models     - Model discovery            |
|  /api/v1/calculate  - Run models (with weather)  |
|  /api/v1/crops      - Crop catalog               |
|  /api/v1/threats    - Threat catalog             |
|  /health, /ready    - Probes                     |
+--------------------------------------------------+
    |
    v
+--------------------------------------------------+
|  Core Library (agstack_pnd)                      |
|                                                  |
|  13 models across 3 layers                       |
|  19 crops, 54 crop-threat pairings              |
|  NOAA weather provider                          |
|  GeoID resolver                                  |
+--------------------------------------------------+
```

The MCP server and REST API share the same process and the same model registry. Tools call the same Python code that the REST API uses. There is no duplication.

---

## Extending the MCP Server

### Adding new tools

If you add a new model or capability to the library, you can expose it as an MCP tool by adding to `src/agstack_pnd/server/mcp_server.py`:

```python
@mcp.tool()
def my_new_tool(param1: str, param2: int) -> dict:
    """Description that the AI agent sees.

    Be specific about what this tool does, what parameters mean,
    and what the return value contains.
    """
    # Call your library code here
    return {"result": "..."}
```

Tool descriptions are critical -- they are what the AI agent reads to decide when and how to call your tool. Write them as if explaining to a knowledgeable colleague.

### Adding new resources

```python
@mcp.resource("pnd://my-resource")
def my_resource() -> str:
    """Description of this resource.

    Resources return text (usually markdown) that agents can load
    for context. Use them for reference data, catalogs, and documentation.
    """
    return "# My Resource\n\nContent here..."
```

---

## Configuration

### Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PND_NOAA_API_TOKEN` | For `/calculate` endpoint | NOAA CDO API token for weather fetching |
| `PND_DATABASE_URL` | For caching/audit | PostgreSQL connection string |
| `PND_AGSTACK_REGISTRY_TOKEN` | For GeoID resolution | AgStack Asset Registry JWT |

The MCP tools that only read the model registry and threat catalog (`list_pest_models`, `get_model_info`, `get_supported_crops_tool`, `get_threats_for_crop_tool`, `explain_threat`) work **without any environment variables**. They read from the bundled catalog and model registry only.

Weather fetching and GeoID resolution require their respective tokens.

### Getting a NOAA API token

1. Go to https://www.ncdc.noaa.gov/cdo-web/token
2. Enter your email
3. Token is emailed instantly (free, no approval needed)

---

## Troubleshooting

### "Connection refused" when connecting to MCP

Make sure the server is running:
```bash
curl http://localhost:8000/health
# Should return: {"status": "ok"}
```

### Agent can't find any tools

Verify the MCP server is mounted:
```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}'
```

### "Module not found" errors

Ensure you installed with server extras:
```bash
pip install "agstack-pnd[server]"
```

The MCP SDK (`mcp` package) is only included in the `[server]` extras.

### Models not appearing in `list_pest_models`

The model registry uses Python entry points for auto-discovery. After installing or updating:
```bash
pip install -e ".[server]"
```

Verify models are registered:
```python
from agstack_pnd.foundation.model_registry import ModelRegistry
r = ModelRegistry()
for m in r.list_models():
    print(f"{m.name}: {m.uuid}")
```

---

## Security Considerations

- The MCP server **does not** require authentication by default. If deploying on a network, put it behind a reverse proxy with auth.
- The server runs on `localhost` by default. Bind to `0.0.0.0` only if you intend network access.
- NOAA tokens and database credentials are passed via environment variables, never in API responses.
- The MCP tools are **read-only** (they query the catalog and registry). The `/calculate` endpoint is the only one that triggers external API calls (NOAA).
- For production deployments, configure CORS origins via `PND_CORS_ORIGINS`.
