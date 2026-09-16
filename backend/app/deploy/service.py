"""
Website deployment orchestration.

Ties together ZIP validation, framework detection, static file
placement, and (for dynamic sites) controlled Docker image building
and container startup.

Static deployment finishes synchronously within the request -- it's
just extracting and moving files, which is fast. Dynamic deployment's
slow parts (Docker image build, container start) run in a FastAPI
BackgroundTask scheduled by the API layer, so the HTTP request returns
immediately with status="building" and the frontend polls
GET /api/websites/{id} for it to become "online" or "failed". This is
the "safest reasonable approach" flagged as acceptable in the Phase 4
brief in place of a full job queue (Celery/Redis) -- see the
"Background deployment" note in docs/WEBSITE-HOSTING.md for the
limitation this implies (an in-flight build is lost if the backend
process restarts mid-build).
"""

import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import SessionLocal
from app.deploy import containers
from app.deploy.builder import INTERNAL_PORTS, write_dockerfile
from app.deploy.detection import detect
from app.deploy.paths import website_storage_dir
from app.deploy.slug import generate_unique_slug
from app.deploy.zip_safety import validate_and_extract_zip
from app.models.user import User
from app.models.website import Website, WebsiteStatus, WebsiteType

_UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MB


# ---------------------------------------------------------------------------
# Ownership / listing
# ---------------------------------------------------------------------------


def get_owned_website(db: Session, user: User, website_id: uuid.UUID) -> Website:
    website = (
        db.query(Website)
        .filter(Website.id == website_id, Website.owner_id == user.id)
        .first()
    )
    if website is None:
        # Same 404 whether the website doesn't exist or belongs to
        # someone else -- never reveal which.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found")
    return website


def list_websites(db: Session, user: User) -> list[Website]:
    return (
        db.query(Website)
        .filter(Website.owner_id == user.id)
        .order_by(Website.created_at.desc())
        .all()
    )


# ---------------------------------------------------------------------------
# Deployment
# ---------------------------------------------------------------------------


def _save_upload_to_temp(upload: UploadFile) -> Path:
    """Stream the uploaded ZIP to a temp file, enforcing the size cap while streaming."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    total = 0
    try:
        with tmp:
            while True:
                chunk = upload.file.read(_UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > settings.max_website_zip_size_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=(
                            "Uploaded ZIP exceeds the maximum allowed size "
                            f"({settings.max_website_zip_size_bytes} bytes)"
                        ),
                    )
                tmp.write(chunk)
    except Exception:
        Path(tmp.name).unlink(missing_ok=True)
        raise
    return Path(tmp.name)


def deploy_website(
    db: Session,
    user: User,
    name: str,
    upload: UploadFile,
    background_tasks: BackgroundTasks,
) -> Website:
    clean_name = (name or "").strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Website name cannot be empty")
    if len(clean_name) > 255:
        raise HTTPException(status_code=400, detail="Website name is too long (max 255 characters)")

    existing_count = db.query(Website.id).filter(Website.owner_id == user.id).count()
    if existing_count >= settings.max_websites_per_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You can only have up to {settings.max_websites_per_user} websites",
        )

    zip_path = _save_upload_to_temp(upload)
    staging_dir = Path(tempfile.mkdtemp(prefix="decp-deploy-"))

    try:
        try:
            validate_and_extract_zip(zip_path, staging_dir)
        finally:
            zip_path.unlink(missing_ok=True)

        site_type, framework, effective_root = detect(staging_dir)
    except Exception:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise

    slug = generate_unique_slug(db, clean_name)
    # Static sites get a trailing slash so relative asset links (e.g.
    # <link href="style.css">) resolve against the site's own path
    # instead of /sites/ -- see app/api/public_sites.py's redirect for
    # what happens if a visitor reaches the URL without one anyway.
    public_url = f"/sites/{slug}/" if site_type == WebsiteType.static else f"/apps/{slug}"

    website = Website(
        owner_id=user.id,
        name=clean_name,
        slug=slug,
        type=site_type,
        framework=framework,
        status=WebsiteStatus.building,
        storage_path=None,
        public_url=public_url,
    )
    db.add(website)
    db.commit()
    db.refresh(website)

    if site_type == WebsiteType.static:
        try:
            final_dir = website_storage_dir(user.id, website.id)
            for item in effective_root.iterdir():
                shutil.move(str(item), str(final_dir / item.name))
            website.storage_path = str(website.id)
            website.status = WebsiteStatus.online
        except Exception as exc:
            website.status = WebsiteStatus.failed
            website.error_message = str(exc)[:2000]
        finally:
            shutil.rmtree(staging_dir, ignore_errors=True)
        db.commit()
        db.refresh(website)
    else:
        # Move the validated project out of the ephemeral /tmp staging
        # area into its permanent, persistent location so the
        # background task can still read it after this request (and
        # its staging dir) would otherwise be gone.
        final_dir = website_storage_dir(user.id, website.id)
        build_dir = final_dir / "build"
        shutil.move(str(effective_root), str(build_dir))
        shutil.rmtree(staging_dir, ignore_errors=True)
        website.storage_path = str(website.id)
        db.commit()
        db.refresh(website)

        background_tasks.add_task(_run_dynamic_deployment, str(website.id), str(build_dir))

    return website


def _run_dynamic_deployment(website_id: str, build_dir: str) -> None:
    """
    Runs in the background after the HTTP request has already
    returned. Opens its own database session -- the request-scoped
    session is closed by the time this executes.
    """
    db = SessionLocal()
    try:
        website = db.query(Website).filter(Website.id == uuid.UUID(website_id)).first()
        if website is None:
            return

        try:
            write_dockerfile(Path(build_dir), website.framework)
            tag = containers.image_tag(website_id)
            containers.build_image(build_dir, tag)

            internal_port = INTERNAL_PORTS[website.framework]
            name = containers.container_name(website_id)
            container_id = containers.run_container(website_id, tag, name, internal_port)

            website.container_id = container_id
            website.internal_port = internal_port
            website.status = WebsiteStatus.online
            website.error_message = None
        except Exception as exc:
            website.status = WebsiteStatus.failed
            website.error_message = str(exc)[:2000]

        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Lifecycle: start / stop / restart / logs
# ---------------------------------------------------------------------------


def _require_dynamic_with_container(website: Website) -> None:
    if website.type != WebsiteType.dynamic:
        raise HTTPException(status_code=400, detail="Only dynamic websites can be started/stopped/restarted")
    if not website.container_id:
        raise HTTPException(status_code=409, detail="This website has no deployed container yet")


def start_website(db: Session, user: User, website_id: uuid.UUID) -> Website:
    website = get_owned_website(db, user, website_id)
    _require_dynamic_with_container(website)
    try:
        containers.start_container(website.container_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    website.status = WebsiteStatus.online
    db.commit()
    db.refresh(website)
    return website


def stop_website(db: Session, user: User, website_id: uuid.UUID) -> Website:
    website = get_owned_website(db, user, website_id)
    _require_dynamic_with_container(website)
    containers.stop_container(website.container_id)
    website.status = WebsiteStatus.stopped
    db.commit()
    db.refresh(website)
    return website


def restart_website(db: Session, user: User, website_id: uuid.UUID) -> Website:
    website = get_owned_website(db, user, website_id)
    _require_dynamic_with_container(website)
    try:
        containers.restart_container(website.container_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    website.status = WebsiteStatus.online
    db.commit()
    db.refresh(website)
    return website


def get_website_logs(db: Session, user: User, website_id: uuid.UUID) -> str:
    website = get_owned_website(db, user, website_id)
    if website.type != WebsiteType.dynamic or not website.container_id:
        raise HTTPException(
            status_code=400, detail="Logs are only available for deployed dynamic websites"
        )
    return containers.get_logs(website.container_id)


# ---------------------------------------------------------------------------
# Deletion
# ---------------------------------------------------------------------------


def reconnect_all_dynamic_websites() -> None:
    """
    Reconnect the backend to every online dynamic website's Docker
    network. Intended to run once at backend startup (see app/main.py)
    to repair the backend↔container network links that a container
    recreation (e.g. `docker compose up` after `down`, or a rebuild)
    would otherwise silently drop -- see
    containers.ensure_backend_connected for the full explanation.
    """
    db = SessionLocal()
    try:
        websites = (
            db.query(Website)
            .filter(Website.type == WebsiteType.dynamic, Website.container_id.isnot(None))
            .all()
        )
        for website in websites:
            containers.ensure_backend_connected(str(website.id))
    finally:
        db.close()


def delete_website(db: Session, user: User, website_id: uuid.UUID) -> None:
    website = get_owned_website(db, user, website_id)
    website.status = WebsiteStatus.deleting
    db.commit()

    if website.type == WebsiteType.dynamic:
        containers.remove_container_and_network(str(website.id), website.container_id)
        containers.remove_image(containers.image_tag(str(website.id)))

    site_dir = website_storage_dir(website.owner_id, website.id)
    shutil.rmtree(site_dir, ignore_errors=True)

    db.delete(website)
    db.commit()
