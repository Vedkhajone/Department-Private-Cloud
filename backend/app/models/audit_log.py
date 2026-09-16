"""
Audit log ORM model.

Answers "who did what" -- as opposed to app/models/system_metric.py,
which answers "what was the server doing" (technical metrics, no
actor). See app/admin/audit.py for how entries are written and
docs/ADMIN-DASHBOARD.md for the full picture.

Deliberately excluded from every row, by construction (see
app/admin/audit.py -- there is no field or code path that could ever
populate one): passwords, password hashes, JWT tokens/secrets, and
uploaded file contents.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_actor_id", "actor_id"),
        Index("ix_audit_logs_action", "action"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Nullable: a few events (e.g. a failed login with an email that
    # doesn't match any account) have no known actor.
    actor_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # A short, fixed machine-readable code, e.g. "website.deploy",
    # "file.delete", "login.failure" -- see app/admin/audit.py for the
    # full list of actions actually recorded.
    action: Mapped[str] = mapped_column(String(64), nullable=False)

    # What kind of thing the action was performed on, e.g. "website",
    # "file", "folder", "user" -- and its id, kept as a string since
    # resource ids vary in type (int for users/files, UUID for
    # websites).
    resource_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Short, human-readable summary shown in the activity log UI, e.g.
    # 'Deployed website "Ved Portfolio"'. Never includes file contents
    # or secrets -- just a name/identifier.
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
