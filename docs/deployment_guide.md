# Deployment Guide

## Option 1: Docker Compose (recommended)

```bash
cd docker
cp .env.example .env
# Edit .env with your NOAA API token
docker compose up -d
```

The API is available at `http://localhost:8000`. MCP server at `http://localhost:8000/mcp`.

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
