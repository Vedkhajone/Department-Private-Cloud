"""
Admin dashboard business logic: overview aggregation, user
management, storage/website reporting, system health, and container
listing. Every function here is only ever reachable through
app/api/admin.py, which requires the `require_admin` dependency on
every route -- see docs/ADMIN-DASHBOARD.md for the full security
model.
"""

import uuid
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import HTTPException, status
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.admin import metrics
from app.admin.audit import record as record_audit
from app.config import settings
from app.deploy import containers
from app.deploy.paths import website_storage_dir
from app.models.file import File
from app.models.folder import Folder
from app.models.system_metric import SystemMetric
from app.models.user import User, UserRole
from app.models.website import Website, WebsiteStatus, WebsiteType
from app.schemas.admin import ServiceStatus

import shutil


# ---------------------------------------------------------------------------
# Service health
# ---------------------------------------------------------------------------


def _check_database(db: Session) -> ServiceStatus:
    try:
        db.execute(text("SELECT 1"))  # trivial round-trip query
        return ServiceStatus(name="Database", status="healthy")
    except Exception as exc:
        return ServiceStatus(name="Database", status="unavailable", detail=str(exc)[:200])


def _check_nginx() -> ServiceStatus:
    try:
        resp = httpx.get("http://nginx/api/health", timeout=2.0)
        if resp.status_code == 200:
            return ServiceStatus(name="NGINX", status="healthy")
        return ServiceStatus(name="NGINX", status="unavailable", detail=f"HTTP {resp.status_code}")
    except Exception as exc:
        return ServiceStatus(name="NGINX", status="unavailable", detail=str(exc)[:200])


def _check_docker() -> ServiceStatus:
    if containers.docker_available():
        return ServiceStatus(name="Docker", status="healthy")
    return ServiceStatus(name="Docker", status="unavailable")


def _check_storage() -> ServiceStatus:
    try:
        usage = shutil.disk_usage(settings.storage_root)
        if usage.total > 0:
            return ServiceStatus(name="Storage", status="healthy")
        return ServiceStatus(name="Storage", status="unavailable")
    except Exception as exc:
        return ServiceStatus(name="Storage", status="unavailable", detail=str(exc)[:200])


def check_services(db: Session) -> list[ServiceStatus]:
    return [
        ServiceStatus(name="API", status="healthy"),  # trivially true -- this code is running
        _check_database(db),
        _check_nginx(),
        _check_docker(),
        _check_storage(),
    ]


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------


def get_overview(db: Session) -> dict:
    total_users = db.query(func.count(User.id)).scalar() or 0

    month_start = datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    new_users_this_month = (
        db.query(func.count(User.id)).filter(User.created_at >= month_start).scalar() or 0
    )

    storage_used_bytes = int(db.query(func.coalesce(func.sum(File.size), 0)).scalar() or 0)
    try:
        disk = shutil.disk_usage(settings.storage_root)
        storage_capacity_bytes = disk.total
    except OSError:
        storage_capacity_bytes = 0
    storage_percent = (
        (storage_used_bytes / storage_capacity_bytes * 100) if storage_capacity_bytes else 0.0
    )

    websites_static = (
        db.query(func.count(Website.id)).filter(Website.type == WebsiteType.static).scalar() or 0
    )
    websites_dynamic = (
        db.query(func.count(Website.id)).filter(Website.type == WebsiteType.dynamic).scalar() or 0
    )

    services = check_services(db)
    services_online = sum(1 for s in services if s.status == "healthy")

    return {
        "total_users": total_users,
        "new_users_this_month": new_users_this_month,
        "storage_used_bytes": storage_used_bytes,
        "storage_capacity_bytes": storage_capacity_bytes,
        "storage_percent": round(storage_percent, 2),
        "websites_total": websites_static + websites_dynamic,
        "websites_static": websites_static,
        "websites_dynamic": websites_dynamic,
        "services_online": services_online,
        "services_total": len(services),
        "services": services,
    }


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


def _storage_used_subquery(db: Session):
    return (
        db.query(File.user_id, func.coalesce(func.sum(File.size), 0).label("used"))
        .group_by(File.user_id)
        .subquery()
    )


def _website_count_subquery(db: Session):
    return (
        db.query(Website.owner_id, func.count(Website.id).label("count"))
        .group_by(Website.owner_id)
        .subquery()
    )


def list_users(db: Session, search: str | None, page: int, page_size: int) -> tuple[list[dict], int]:
    query = db.query(User)
    if search:
        like = f"%{search.strip()}%"
        query = query.filter(
            (User.name.ilike(like)) | (User.email.ilike(like)) | (User.roll_number.ilike(like))
        )

    total = query.with_entities(func.count(User.id)).scalar() or 0

    users = (
        query.order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    storage_sub = _storage_used_subquery(db)
    website_sub = _website_count_subquery(db)
    storage_by_user = dict(db.query(storage_sub.c.user_id, storage_sub.c.used).all())
    websites_by_user = dict(db.query(website_sub.c.owner_id, website_sub.c.count).all())

    items = [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "roll_number": u.roll_number,
            "role": u.role,
            "is_active": u.is_active,
            "storage_used_bytes": int(storage_by_user.get(u.id, 0)),
            "storage_limit_bytes": u.storage_limit * 1024 * 1024,
            "website_count": int(websites_by_user.get(u.id, 0)),
            "created_at": u.created_at,
        }
        for u in users
    ]
    return items, total


def get_user_detail(db: Session, user_id: int) -> dict:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    storage_used = int(
        db.query(func.coalesce(func.sum(File.size), 0)).filter(File.user_id == user_id).scalar()
        or 0
    )
    file_count = db.query(func.count(File.id)).filter(File.user_id == user_id).scalar() or 0
    folder_count = db.query(func.count(Folder.id)).filter(Folder.user_id == user_id).scalar() or 0
    websites = (
        db.query(Website).filter(Website.owner_id == user_id).order_by(Website.created_at.desc()).all()
    )

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "roll_number": user.roll_number,
        "role": user.role,
        "is_active": user.is_active,
        "storage_used_bytes": storage_used,
        "storage_limit_bytes": user.storage_limit * 1024 * 1024,
        "file_count": file_count,
        "folder_count": folder_count,
        "websites": websites,
        "created_at": user.created_at,
    }


def change_user_role(db: Session, actor: User, user_id: int, new_role: UserRole) -> User:
    if actor.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role",
        )

    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    old_role = target.role
    target.role = new_role
    db.commit()
    db.refresh(target)

    record_audit(
        db,
        actor_id=actor.id,
        action="admin.role_change",
        resource_type="user",
        resource_id=target.id,
        description=f"Changed {target.email}'s role from {old_role.value} to {new_role.value}",
    )
    return target


def change_user_active(db: Session, actor: User, user_id: int, is_active: bool) -> User:
    if actor.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot disable your own account",
        )

    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    target.is_active = is_active
    db.commit()
    db.refresh(target)

    record_audit(
        db,
        actor_id=actor.id,
        action="admin.account_status_change",
        resource_type="user",
        resource_id=target.id,
        description=f"{'Enabled' if is_active else 'Disabled'} {target.email}'s account",
    )
    return target


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------


def get_storage_overview(db: Session, top_n: int = 10) -> dict:
    try:
        disk = shutil.disk_usage(settings.storage_root)
        capacity_bytes = disk.total
    except OSError:
        capacity_bytes = 0

    used_bytes = int(db.query(func.coalesce(func.sum(File.size), 0)).scalar() or 0)
    available_bytes = max(capacity_bytes - used_bytes, 0)
    used_percent = (used_bytes / capacity_bytes * 100) if capacity_bytes else 0.0

    if used_percent >= settings.storage_critical_percent:
        health = "critical"
    elif used_percent >= settings.storage_warning_percent:
        health = "warning"
    else:
        health = "normal"

    file_count = db.query(func.count(File.id)).scalar() or 0
    folder_count = db.query(func.count(Folder.id)).scalar() or 0
    user_count = db.query(func.count(User.id)).scalar() or 0

    top_rows = (
        db.query(User.id, User.name, User.email, func.coalesce(func.sum(File.size), 0).label("used"))
        .join(File, File.user_id == User.id)
        .group_by(User.id, User.name, User.email)
        .order_by(func.sum(File.size).desc())
        .limit(top_n)
        .all()
    )
    top_users = [
        {"user_id": r[0], "name": r[1], "email": r[2], "storage_used_bytes": int(r[3])}
        for r in top_rows
    ]

    return {
        "capacity_bytes": capacity_bytes,
        "used_bytes": used_bytes,
        "available_bytes": available_bytes,
        "used_percent": round(used_percent, 2),
        "health": health,
        "warning_threshold_percent": settings.storage_warning_percent,
        "critical_threshold_percent": settings.storage_critical_percent,
        "file_count": file_count,
        "folder_count": folder_count,
        "user_count": user_count,
        "top_users": top_users,
    }


# ---------------------------------------------------------------------------
# Websites (admin)
# ---------------------------------------------------------------------------


def list_websites_admin(
    db: Session,
    search: str | None,
    status_filter: WebsiteStatus | None,
    type_filter: WebsiteType | None,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    query = db.query(Website, User).join(User, Website.owner_id == User.id)

    if search:
        like = f"%{search.strip()}%"
        query = query.filter((Website.name.ilike(like)) | (User.email.ilike(like)))
    if status_filter:
        query = query.filter(Website.status == status_filter)
    if type_filter:
        query = query.filter(Website.type == type_filter)

    total = query.with_entities(func.count(Website.id)).scalar() or 0

    rows = (
        query.order_by(Website.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [
        {
            "id": w.id,
            "name": w.name,
            "slug": w.slug,
            "type": w.type,
            "framework": w.framework,
            "status": w.status,
            "public_url": w.public_url,
            "error_message": w.error_message,
            "owner_id": u.id,
            "owner_name": u.name,
            "owner_email": u.email,
            "created_at": w.created_at,
            "updated_at": w.updated_at,
        }
        for w, u in rows
    ]
    return items, total


def get_website_admin(db: Session, website_id: uuid.UUID) -> Website:
    """
    Like app.deploy.service.get_owned_website, but for admins: looks
    up any website by id with no owner restriction (admin access is
    already enforced by the route's require_admin dependency).
    """
    website = db.get(Website, website_id)
    if website is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found")
    return website


def _require_dynamic_with_container(website: Website) -> None:
    if website.type != WebsiteType.dynamic:
        raise HTTPException(status_code=400, detail="Only dynamic websites can be started/stopped/restarted")
    if not website.container_id:
        raise HTTPException(status_code=409, detail="This website has no deployed container yet")


def admin_stop_website(db: Session, actor: User, website_id: uuid.UUID) -> Website:
    website = get_website_admin(db, website_id)
    _require_dynamic_with_container(website)
    containers.stop_container(website.container_id)
    website.status = WebsiteStatus.stopped
    db.commit()
    db.refresh(website)
    record_audit(
        db, actor_id=actor.id, action="website.stop", resource_type="website",
        resource_id=website.id, description=f'Stopped website "{website.name}"',
    )
    return website


def admin_restart_website(db: Session, actor: User, website_id: uuid.UUID) -> Website:
    website = get_website_admin(db, website_id)
    _require_dynamic_with_container(website)
    try:
        containers.restart_container(website.container_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    website.status = WebsiteStatus.online
    db.commit()
    db.refresh(website)
    record_audit(
        db, actor_id=actor.id, action="website.restart", resource_type="website",
        resource_id=website.id, description=f'Restarted website "{website.name}"',
    )
    return website


def admin_delete_website(db: Session, actor: User, website_id: uuid.UUID) -> None:
    website = get_website_admin(db, website_id)
    name, owner_id, site_id = website.name, website.owner_id, website.id

    website.status = WebsiteStatus.deleting
    db.commit()

    if website.type == WebsiteType.dynamic:
        containers.remove_container_and_network(str(website.id), website.container_id)
        containers.remove_image(containers.image_tag(str(website.id)))

    shutil.rmtree(website_storage_dir(owner_id, site_id), ignore_errors=True)

    db.delete(website)
    db.commit()

    record_audit(
        db, actor_id=actor.id, action="website.delete", resource_type="website",
        resource_id=site_id, description=f'Deleted website "{name}" (owner user #{owner_id})',
    )


def get_website_logs_admin(website: Website) -> str:
    if website.type != WebsiteType.dynamic or not website.container_id:
        raise HTTPException(status_code=400, detail="Logs are only available for deployed dynamic websites")
    return containers.get_logs(website.container_id)


# ---------------------------------------------------------------------------
# System / metrics / containers
# ---------------------------------------------------------------------------


def get_system_snapshot(db: Session) -> dict:
    snapshot = metrics.collect_snapshot()
    snapshot["services"] = check_services(db)
    return snapshot


_RANGE_TO_TIMEDELTA = {
    "1h": timedelta(hours=1),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}


def get_metrics_history(db: Session, range_key: str) -> list[SystemMetric]:
    delta = _RANGE_TO_TIMEDELTA.get(range_key)
    if delta is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported range '{range_key}'. Use one of: {', '.join(_RANGE_TO_TIMEDELTA)}",
        )
    since = datetime.now(timezone.utc) - delta
    return metrics.history(db, since)


def list_containers(db: Session) -> list[dict]:
    raw = containers.list_managed_containers()

    # Map container id -> (website id, website name) for display.
    by_container_id = {
        w.container_id: (w.id, w.name)
        for w in db.query(Website).filter(Website.container_id.isnot(None)).all()
    }

    result = []
    for c in raw:
        stats = containers.container_stats(c["id"]) or {}
        website_id, website_name = by_container_id.get(c["id"], (None, None))
        result.append(
            {
                "id": c["id"],
                "name": c["name"],
                "status": c["status"],
                "image": c["image"],
                "cpu_percent": stats.get("cpu_percent"),
                "memory_bytes": stats.get("memory_bytes"),
                "memory_limit_bytes": stats.get("memory_limit_bytes"),
                "website_id": website_id,
                "website_name": website_name,
            }
        )
    return result


def get_container_logs(container_id: str) -> str:
    return containers.get_logs(container_id)


# ---------------------------------------------------------------------------
# Audit logs
# ---------------------------------------------------------------------------


def list_audit_logs(
    db: Session,
    actor_id: int | None,
    action: str | None,
    since: datetime | None,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    from app.models.audit_log import AuditLog  # local import avoids a module cycle

    query = db.query(AuditLog, User).outerjoin(User, AuditLog.actor_id == User.id)

    if actor_id is not None:
        query = query.filter(AuditLog.actor_id == actor_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if since is not None:
        query = query.filter(AuditLog.created_at >= since)

    total = query.with_entities(func.count(AuditLog.id)).scalar() or 0

    rows = (
        query.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [
        {
            "id": log.id,
            "actor_id": log.actor_id,
            "actor_name": user.name if user else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "description": log.description,
            "ip_address": log.ip_address,
            "created_at": log.created_at,
        }
        for log, user in rows
    ]
    return items, total


def get_audit_log(db: Session, log_id: int) -> dict:
    from app.models.audit_log import AuditLog  # local import avoids a module cycle

    row = (
        db.query(AuditLog, User)
        .outerjoin(User, AuditLog.actor_id == User.id)
        .filter(AuditLog.id == log_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log entry not found")

    log, user = row
    return {
        "id": log.id,
        "actor_id": log.actor_id,
        "actor_name": user.name if user else None,
        "action": log.action,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
        "description": log.description,
        "ip_address": log.ip_address,
        "created_at": log.created_at,
    }
