"""FastAPI application factory with MCP server integration."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from agstack_pnd import __version__
from agstack_pnd.server.routers import calculate, health, models


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # TODO: init DB pool, APScheduler for weather sync
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="AgStack Pest & Disease Models",
        version=__version__,
        description="Hierarchical pest and disease modeling API for AgStack (Linux Foundation)",
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(models.router, prefix="/api/v1")
    app.include_router(calculate.router, prefix="/api/v1")

    _mount_mcp(app)

    return app


def _mount_mcp(app: FastAPI) -> None:
    """Mount the MCP server on /mcp using Streamable HTTP transport."""
    try:
        from agstack_pnd.server.mcp_server import mcp

        mcp_app = mcp.streamable_http_app()
        app.mount("/mcp", mcp_app)
    except ImportError:
        pass
