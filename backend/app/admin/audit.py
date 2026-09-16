"""
Audit logging.

record() is the single write path for every audit_logs row in the
system -- called from the handful of endpoints/services listed below,
never from the frontend directly. Keeping it to one small, reviewed
function is what guarantees a row can never accidentally end up
holding a password, password hash, JWT, or file content: those values
are simply never passed to it anywhere in the codebase.

Recorded today (see docs/ADMIN-DASHBOARD.md for the rationale):
  auth.register, auth.login_success, auth.login_failure,
  file.upload, file.delete, folder.create, folder.delete,
  website.deploy, website.delete, website.restart, website.stop,
  admin.role_change, admin.account_status_change

Deliberately NOT logged: routine reads (listing files, viewing a
dashboard), renames, folder navigation -- useful auditing, not noise.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def record(
    db: Session,
    *,
    actor_id: int | None,
    action: str,
    resource_type: str | None = None,
    resource_id: Any = None,
    description: str | None = None,
    ip_address: str | None = None,
) -> None:
    """
    Insert one audit log row and commit it immediately, in its own
    small transaction -- so a later failure/rollback in the caller's
    main operation (e.g. the DB insert for a new file) can't also
    silently wipe out the audit trail for it, and vice versa: a
    logging problem is caught and swallowed here rather than ever
    failing the actual user-facing operation it's describing.
    """
    try:
        entry = AuditLog(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            description=description,
            ip_address=ip_address,
        )
        db.add(entry)
        db.commit()
    except Exception:
        db.rollback()
        # Auditing is best-effort: never let a logging failure break
        # the real operation it's recording.
