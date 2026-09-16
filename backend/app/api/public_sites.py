"""
Public website serving: /sites/<slug>/... (static) and
/apps/<slug>/... (dynamic, reverse-proxied to the site's container).

Deliberately unauthenticated -- a hosted website is meant to be
publicly viewable, the same way any other web host works. NGINX
forwards everything under these two prefixes here (see
nginx/nginx.conf) exactly like it forwards /api/ to the rest of the
backend; the browser only ever talks to NGINX.

Static files are served directly from disk with the same path-
containment guard used throughout the storage layer. Dynamic requests
are reverse-proxied over the website's dedicated Docker network to its
container, addressed by container name (Docker's built-in per-network
DNS) -- never by a published host port.
"""

import mimetypes

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.deploy.paths import website_storage_dir
from app.models.website import Website, WebsiteStatus, WebsiteType
from app.storage.paths import STORAGE_ROOT, ensure_inside_storage_root

sites_router = APIRouter(prefix="/sites", tags=["public-sites"])
apps_router = APIRouter(prefix="/apps", tags=["public-sites"])

_HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-length",
    "host",
}


def _find_static_website(db: Session, slug: str) -> Website:
    website = (
        db.query(Website)
        .filter(Website.slug == slug, Website.type == WebsiteType.static)
        .first()
    )
    if website is None or website.status != WebsiteStatus.online:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found")
    return website


def _find_dynamic_website(db: Session, slug: str) -> Website:
    website = (
        db.query(Website)
        .filter(Website.slug == slug, Website.type == WebsiteType.dynamic)
        .first()
    )
    if website is None or website.status != WebsiteStatus.online or not website.container_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Website not found or not running"
        )
    return website


def _serve_static(slug: str, subpath: str, db: Session) -> FileResponse:
    website = _find_static_website(db, slug)
    root = website_storage_dir(website.owner_id, website.id)

    requested = subpath or "index.html"
    target = (root / requested).resolve()

    # The real traversal guard: no matter what `requested` looks like,
    # the resolved path must stay inside both this website's directory
    # and STORAGE_ROOT overall.
    if (target != root and root not in target.parents) or (
        target != STORAGE_ROOT and STORAGE_ROOT not in target.parents
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if target.is_dir():
        target = target / "index.html"

    if not target.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    media_type, _ = mimetypes.guess_type(str(target))
    return FileResponse(target, media_type=media_type)


@sites_router.get("/{slug}")
def serve_static_root(slug: str, db: Session = Depends(get_db)) -> Response:
    # Redirect the bare slug ("/sites/my-site") to the slash-terminated
    # form ("/sites/my-site/") *before* serving index.html, the same
    # way a normal web server handles a directory URL. Without this, a
    # relative asset link in the page (e.g. `<link href="style.css">`)
    # resolves against "/sites/" instead of "/sites/my-site/" and 404s
    # -- the site "loses" its CSS/JS even though the files are right
    # there on disk. Validate the site exists first so an unknown slug
    # still 404s instead of redirecting to a dead end.
    _find_static_website(db, slug)
    return RedirectResponse(url=f"/sites/{slug}/", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@sites_router.get("/{slug}/{subpath:path}")
def serve_static_path(slug: str, subpath: str, db: Session = Depends(get_db)) -> FileResponse:
    return _serve_static(slug, subpath, db)


async def _proxy_dynamic(slug: str, subpath: str, request: Request, db: Session) -> Response:
    website = _find_dynamic_website(db, slug)

    from app.deploy.containers import container_name  # local import avoids a cycle at module load

    target_url = f"http://{container_name(str(website.id))}:{website.internal_port}/{subpath}"

    body = await request.body()
    forward_headers = {
        k: v for k, v in request.headers.items() if k.lower() not in _HOP_BY_HOP_HEADERS
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            upstream = await client.request(
                request.method,
                target_url,
                params=request.query_params,
                content=body,
                headers=forward_headers,
            )
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, detail="The application is not responding"
            )

    response_headers = {
        k: v for k, v in upstream.headers.items() if k.lower() not in _HOP_BY_HOP_HEADERS
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )


_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


@apps_router.api_route("/{slug}", methods=_METHODS)
async def proxy_dynamic_root(slug: str, request: Request, db: Session = Depends(get_db)) -> Response:
    return await _proxy_dynamic(slug, "", request, db)


@apps_router.api_route("/{slug}/{subpath:path}", methods=_METHODS)
async def proxy_dynamic_path(
    slug: str, subpath: str, request: Request, db: Session = Depends(get_db)
) -> Response:
    return await _proxy_dynamic(slug, subpath, request, db)
