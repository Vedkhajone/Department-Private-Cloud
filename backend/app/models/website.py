"""
Website ORM model.

A website is either `static` (served directly as files) or `dynamic`
(served by proxying to an isolated Docker container). See
app/deploy/service.py for the deployment logic and
docs/WEBSITE-HOSTING.md for the full architecture.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class WebsiteType(str, enum.Enum):
    static = "static"
    dynamic = "dynamic"


class WebsiteFramework(str, enum.Enum):
    html = "html"
    react = "react"
    flask = "flask"
    fastapi = "fastapi"
    node = "node"


class WebsiteStatus(str, enum.Enum):
    pending = "pending"
    building = "building"
    online = "online"
    stopped = "stopped"
    failed = "failed"
    deleting = "deleting"


class Website(Base):
    __tablename__ = "websites"

    # UUID primary key: website ids are exposed in the API/URLs, so an
    # unguessable, non-sequential id is preferable to a plain integer
    # here (unlike users/folders/files, which are never exposed as
    # cross-user-comparable ids in a public-facing way).
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Public, URL-safe identifier -- see app/deploy/slug.py. Always
    # server-generated from `name`, never client-supplied directly.
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)

    type: Mapped[WebsiteType] = mapped_column(Enum(WebsiteType, name="website_type"), nullable=False)
    framework: Mapped[WebsiteFramework] = mapped_column(
        Enum(WebsiteFramework, name="website_framework"), nullable=False
    )
    status: Mapped[WebsiteStatus] = mapped_column(
        Enum(WebsiteStatus, name="website_status"), nullable=False, default=WebsiteStatus.pending
    )

    # Relative identifier for the website's directory under
    # STORAGE_ROOT/websites/<owner_id>/ -- see app/deploy/paths.py.
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Dynamic websites only: the running container's id/name and the
    # port its app listens on *inside* the container (never published
    # to the host -- see app/deploy/containers.py).
    container_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    internal_port: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relative path, e.g. "/sites/my-portfolio" or "/apps/my-flask-app"
    # -- deliberately never an absolute URL with a hardcoded host, so
    # it keeps working if the server's address changes.
    public_url: Mapped[str | None] = mapped_column(String(255), nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
