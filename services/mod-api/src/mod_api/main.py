"""Pedalboard API main application entry point."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import (
    pedalboards_router,
    effects_router,
    connections_router,
    ports_router,
    parameters_router,
)
from .utils.mod_host_client import ModHostClient
from .storage.pedalboard_store import PedalboardStore
from .effects.registry import EffectsRegistry


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - initialize on startup.

    Args:
        app: The FastAPI application instance.

    Yields:
        Control back to the application after setup.
    """
    # Create instances from environment configuration
    mod_host_host = os.getenv("MOD_HOST_HOST", "127.0.0.1")
    mod_host_port = int(os.getenv("MOD_HOST_PORT", "5555"))
    mod_host_fb_port = int(os.getenv("MOD_HOST_FB_PORT", "5556"))
    data_dir = os.getenv("PEDALBOARD_DATA_DIR", "/var/mod/pedalboards")

    client = ModHostClient(host=mod_host_host, port=mod_host_port, fb_port=mod_host_fb_port)
    store = PedalboardStore(data_dir=data_dir)
    registry = EffectsRegistry()

    # Initialize and load state
    client.connect()
    registry.discover()

    # Clear any existing plugins from mod-host (ensures clean state for testing)
    client.remove_plugin(-1)

    # Store in app.state for lifespan-based dependency injection
    app.state.pedalboard_store = store
    app.state.effects_registry = registry
    app.state.mod_host_client = client

    yield

    # Cleanup on shutdown
    client.close()


# Create FastAPI application
app = FastAPI(
    title="Pedalboard API",
    description="REST API for managing pedalboards, effects, and connections on MOD Audio platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Include all routers with /api/v1 prefix
app.include_router(pedalboards_router, prefix="/api/v1")
app.include_router(effects_router, prefix="/api/v1")
app.include_router(connections_router, prefix="/api/v1")
app.include_router(ports_router, prefix="/api/v1")
app.include_router(parameters_router, prefix="/api/v1")


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint.

    Returns a simple status check for container orchestration and monitoring.

    Returns:
        JSON response with status "ok".
    """
    return {"status": "ok"}