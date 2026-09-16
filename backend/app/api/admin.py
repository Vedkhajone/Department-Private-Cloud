"""
Admin API. Every route below depends on `require_admin` -- decoded
from the JWT the same way as every other authenticated endpoint, then
checked against `role == admin` (app/auth/dependencies.py). There is
no separate "admin session" mechanism and no route here trusts a
client-supplied role or user id for anything.
"""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.admin import service
from app.auth.dependencies import require_admin
from app.db.database import get_db
from app.models.user import User, UserRole
from app.models.website import WebsiteStatus, WebsiteType
from app.schemas.admin import (
    ActiveStatusChangeRequest,
    AdminUserDetail,
    AdminUserListResponse,
    AdminWebsiteResponse,
    AuditLogEntry,
    AuditLogListResponse,
    ContainerLogsResponse,
    ContainerSummary,
    MetricsHistoryResponse,
    OverviewResponse,
    RoleChangeRequest,
    StorageOverviewResponse,
    SystemSnapshotResponse,
)

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------


@router.get("/overview", response_model=OverviewResponse)
def get_overview(db: Session = Depends(get_db)):
    return service.get_overview(db)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


@router.get("/users", response_model=AdminUserListResponse)
def list_users(
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = service.list_users(db, search, page, page_size)
    return AdminUserListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/users/{user_id}", response_model=AdminUserDetail)
def get_user_detail(user_id: int, db: Session = Depends(get_db)):
    return service.get_user_detail(db, user_id)


@router.patch("/users/{user_id}/role", response_model=AdminUserDetail)
def change_user_role(
    user_id: int,
    payload: RoleChangeRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service.change_user_role(db, admin, user_id, payload.role)
    return service.get_user_detail(db, user_id)


@router.patch("/users/{user_id}/active", response_model=AdminUserDetail)
def change_user_active(
    user_id: int,
    payload: ActiveStatusChangeRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service.change_user_active(db, admin, user_id, payload.is_active)
    return service.get_user_detail(db, user_id)


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------


@router.get("/storage", response_model=StorageOverviewResponse)
def get_storage_overview(db: Session = Depends(get_db)):
    return service.get_storage_overview(db)


# ---------------------------------------------------------------------------
# Websites
# ---------------------------------------------------------------------------


@router.get("/websites", response_model=list[AdminWebsiteResponse])
def list_websites(
    search: str | None = Query(default=None),
    status_filter: WebsiteStatus | None = Query(default=None, alias="status"),
    type_filter: WebsiteType | None = Query(default=None, alias="type"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    items, _total = service.list_websites_admin(db, search, status_filter, type_filter, page, page_size)
    return items


def _website_to_admin_dict(db: Session, website) -> dict:
    owner = db.get(User, website.owner_id)
    return {
        "id": website.id,
        "name": website.name,
        "slug": website.slug,
        "type": website.type,
        "framework": website.framework,
        "status": website.status,
        "public_url": website.public_url,
        "error_message": website.error_message,
        "owner_id": website.owner_id,
        "owner_name": owner.name if owner else "(deleted user)",
        "owner_email": owner.email if owner else "",
        "created_at": website.created_at,
        "updated_at": website.updated_at,
    }


@router.get("/websites/{website_id}", response_model=AdminWebsiteResponse)
def get_website(website_id: uuid.UUID, db: Session = Depends(get_db)):
    website = service.get_website_admin(db, website_id)
    return _website_to_admin_dict(db, website)


@router.post("/websites/{website_id}/stop", response_model=AdminWebsiteResponse)
def stop_website(website_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    website = service.admin_stop_website(db, admin, website_id)
    return _website_to_admin_dict(db, website)


@router.post("/websites/{website_id}/restart", response_model=AdminWebsiteResponse)
def restart_website(website_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    website = service.admin_restart_website(db, admin, website_id)
    return _website_to_admin_dict(db, website)


@router.delete("/websites/{website_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_website(website_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> None:
    service.admin_delete_website(db, admin, website_id)


@router.get("/websites/{website_id}/logs", response_model=ContainerLogsResponse)
def get_website_logs(website_id: uuid.UUID, db: Session = Depends(get_db)):
    website = service.get_website_admin(db, website_id)
    return ContainerLogsResponse(logs=service.get_website_logs_admin(website))


# ---------------------------------------------------------------------------
# System / metrics / containers
# ---------------------------------------------------------------------------


@router.get("/system", response_model=SystemSnapshotResponse)
def get_system_snapshot(db: Session = Depends(get_db)):
    return service.get_system_snapshot(db)


@router.get("/metrics", response_model=MetricsHistoryResponse)
def get_metrics_history(
    range: str = Query(default="1h", pattern="^(1h|24h|7d|30d)$"),
    db: Session = Depends(get_db),
):
    points = service.get_metrics_history(db, range)
    return MetricsHistoryResponse(range=range, points=points)


@router.get("/containers", response_model=list[ContainerSummary])
def list_containers(db: Session = Depends(get_db)):
    return service.list_containers(db)


@router.get("/containers/{container_id}/logs", response_model=ContainerLogsResponse)
def get_container_logs(container_id: str):
    return ContainerLogsResponse(logs=service.get_container_logs(container_id))


# ---------------------------------------------------------------------------
# Audit logs
# ---------------------------------------------------------------------------


@router.get("/audit-logs", response_model=AuditLogListResponse)
def list_audit_logs(
    actor_id: int | None = Query(default=None),
    action: str | None = Query(default=None),
    range: str | None = Query(default=None, pattern="^(24h|7d|30d)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    since = None
    if range:
        delta = {"24h": timedelta(hours=24), "7d": timedelta(days=7), "30d": timedelta(days=30)}[range]
        since = datetime.now(timezone.utc) - delta

    items, total = service.list_audit_logs(db, actor_id, action, since, page, page_size)
    return AuditLogListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/audit-logs/{log_id}", response_model=AuditLogEntry)
def get_audit_log(log_id: int, db: Session = Depends(get_db)):
    return service.get_audit_log(db, log_id)
