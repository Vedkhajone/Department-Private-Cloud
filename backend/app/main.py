"""
DECP backend entry point.

Wires together the FastAPI app and its routers. Endpoint logic lives
in app/api/*, database access in app/db and app/models, request/
response shapes in app/schemas, and auth logic in app/auth -- this
file only assembles them.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, files, folders, storage, users
from app.config import settings

app = FastAPI(title="Department Engineering Cloud API")

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


@app.get("/")
def read_root() -> dict:
    """Basic root endpoint, useful for a manual sanity check."""
    return {
        "message": "Department Engineering Cloud backend is running",
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
