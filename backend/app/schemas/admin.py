"""
Pydantic schemas for the admin API (app/api/admin.py).

None of these ever include password_hash, JWT contents, or raw
filesystem paths -- see app/admin/service.py for how each is built.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import UserRole
from app.models.website import WebsiteFramework, WebsiteStatus, WebsiteType


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------


class ServiceStatus(BaseModel):
    name: str
    status: str  # "healthy" | "unavailable"
    detail: str | None = None


class OverviewResponse(BaseModel):
    total_users: int
    new_users_this_month: int

    storage_used_bytes: int
    storage_capacity_bytes: int
    storage_percent: float

    websites_total: int
    websites_static: int
    websites_dynamic: int

    services_online: int
    services_total: int
    services: list[ServiceStatus]


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


class AdminUserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    roll_number: str | None
    role: UserRole
    is_active: bool
    storage_used_bytes: int
    storage_limit_bytes: int
    website_count: int
    created_at: datetime


class AdminUserListResponse(BaseModel):
    items: list[AdminUserSummary]
    total: int
    page: int
    page_size: int


class AdminWebsiteSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    type: WebsiteType
    framework: WebsiteFramework
    status: WebsiteStatus
    public_url: str | None
    created_at: datetime


class AdminUserDetail(BaseModel):
    id: int
    name: str
    email: EmailStr
    roll_number: str | None
    role: UserRole
    is_active: bool
    storage_used_bytes: int
    storage_limit_bytes: int
    file_count: int
    folder_count: int
    websites: list[AdminWebsiteSummary]
    created_at: datetime


class RoleChangeRequest(BaseModel):
    role: UserRole


class ActiveStatusChangeRequest(BaseModel):
    is_active: bool


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------


class StorageTopUser(BaseModel):
    user_id: int
    name: str
    email: EmailStr
    storage_used_bytes: int


class StorageOverviewResponse(BaseModel):
    capacity_bytes: int
    used_bytes: int
    available_bytes: int
    used_percent: float
    health: str  # "normal" | "warning" | "critical"
    warning_threshold_percent: float
    critical_threshold_percent: float

    file_count: int
    folder_count: int
    user_count: int

    top_users: list[StorageTopUser]


# ---------------------------------------------------------------------------
# Websites (admin view)
# ---------------------------------------------------------------------------


class AdminWebsiteResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    type: WebsiteType
    framework: WebsiteFramework
    status: WebsiteStatus
    public_url: str | None
    error_message: str | None
    owner_id: int
    owner_name: str
    owner_email: EmailStr
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# System / metrics / containers
# ---------------------------------------------------------------------------


class SystemSnapshotResponse(BaseModel):
    cpu_percent: float
    memory_percent: float
    memory_total_bytes: int
    memory_used_bytes: int
    disk_percent: float
    disk_total_bytes: int
    disk_used_bytes: int
    network_rx_bytes: int
    network_tx_bytes: int
    uptime_seconds: float
    services: list[ServiceStatus]


class MetricPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_rx_bytes: int
    network_tx_bytes: int


class MetricsHistoryResponse(BaseModel):
    range: str
    points: list[MetricPoint]


class ContainerSummary(BaseModel):
    id: str
    name: str
    status: str
    image: str
    cpu_percent: float | None = None
    memory_bytes: int | None = None
    memory_limit_bytes: int | None = None
    website_id: uuid.UUID | None = None
    website_name: str | None = None


class ContainerLogsResponse(BaseModel):
    logs: str


# ---------------------------------------------------------------------------
# Audit logs
# ---------------------------------------------------------------------------


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: int | None
    actor_name: str | None
    action: str
    resource_type: str | None
    resource_id: str | None
    description: str | None
    ip_address: str | None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogEntry]
    total: int
    page: int
    page_size: int
