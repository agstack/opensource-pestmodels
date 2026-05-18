# Deployment Guide

All deployment options expose the REST API and MCP server on the same port. For detailed MCP setup (connecting Claude, Cursor, or other AI agents), see the [MCP Server Guide](mcp_server_guide.md).

## Option 1: Docker Compose (recommended)

```bash
git clone https://github.com/agstack/opensource-pestmodels.git
cd opensource-pestmodels/docker
cp .env.example .env
# Edit .env with your NOAA API token
docker compose up -d
```

| Endpoint | URL |
|----------|-----|
| REST API | `http://localhost:8000/api/v1/` |
| MCP Server | `http://localhost:8000/mcp` |
| OpenAPI Docs | `http://localhost:8000/docs` |
| Health Check | `http://localhost:8000/health` |

## Option 2: Direct Python

```bash
pip install "agstack-pnd[server]"

export PND_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/pnd
export PND_NOAA_API_TOKEN=your-token

uvicorn agstack_pnd.server.app:create_app --factory --host 0.0.0.0 --port 8000
```

## Option 3: Library Only (no server)

```bash
pip install agstack-pnd
```

Use models directly in Python:

```python
from agstack_pnd.models.weather.growing_degree_days import GrowingDegreeDays
model = GrowingDegreeDays()
result = model.calculate(weather_data, {"base_temp": 10.0})
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PND_DATABASE_URL` | Server only | PostgreSQL connection string |
| `PND_NOAA_API_TOKEN` | For weather fetching | NOAA CDO API token (free: https://www.ncdc.noaa.gov/cdo-web/token) |
| `PND_AGSTACK_REGISTRY_TOKEN` | Optional | AgStack Asset Registry JWT for GeoID resolution |
| `PND_CORS_ORIGINS` | Optional | Comma-separated allowed origins |
| `PND_DEBUG` | Optional | Enable debug mode (default: false) |

## NOAA API Token

Get a free token at https://www.ncdc.noaa.gov/cdo-web/token. It is emailed to you instantly.

## Related Documentation

- [User Manual](user_manual.md) -- How to use the library, API, and MCP server
- [MCP Server Guide](mcp_server_guide.md) -- Connecting AI agents (Claude, Cursor, custom)
- [Contributor Guide](contributor_guide.md) -- How to add models, providers, threats
- [Architecture Design](design_architecture.md) -- Technical architecture
