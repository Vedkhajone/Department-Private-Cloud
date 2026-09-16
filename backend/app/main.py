"""
DECP backend entry point.

Wires together the FastAPI app and its routers. Endpoint logic lives
in app/api/*, database access in app/db and app/models, request/
response shapes in app/schemas, and auth logic in app/auth -- this
file only assembles them.
"""

import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.admin.metrics import start_sampler
from app.api import admin, auth, files, folders, public_sites, storage, users, websites
from app.config import settings
from app.deploy.service import reconnect_all_dynamic_websites

app = FastAPI(title="ECE DeptCloud API")


@app.on_event("startup")
def _reconnect_dynamic_website_networks() -> None:
    """
    Repair backend↔container Docker network links for already-deployed
    dynamic websites on every backend startup -- see
    app/deploy/service.py:reconnect_all_dynamic_websites for why this
    is necessary (in short: those links aren't tracked by Docker
    Compose, so recreating this container would otherwise silently
    break reverse-proxying to every dynamic site until it's
    redeployed).
    """
    reconnect_all_dynamic_websites()


@app.on_event("startup")
async def _start_metrics_sampler() -> None:
    """
    Launches the periodic system-metrics sampler (app/admin/metrics.py)
    as a background asyncio task for the lifetime of the process --
    powers the admin dashboard's server health history graphs.
    """
    asyncio.create_task(start_sampler())

# CORS is permissive for local development only. This should be
# tightened once the frontend is served exclusively through NGINX
# and real domains are known.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(folders.router)
app.include_router(files.router)
app.include_router(storage.router)
app.include_router(websites.router)
app.include_router(public_sites.sites_router)
app.include_router(public_sites.apps_router)
app.include_router(admin.router)


@app.get("/")
def read_root() -> dict:
    """Basic root endpoint, useful for a manual sanity check."""
    return {
        "message": "ECE DeptCloud backend is running",
        "environment": settings.environment,
    }


@app.get("/api/health")
def health_check() -> dict:
    """
    Health endpoint used by the frontend (and later, monitoring)
    to confirm the backend is up and reachable.
    """
    return {
        "status": "ok",
        "service": settings.service_name,
    }
