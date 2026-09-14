"""
User ORM model.

This is the database representation of a user (student, faculty, or
admin). It defines table structure only -- request/response shaping
belongs in app/schemas/user.py.
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class UserRole(str, enum.Enum):
    student = "student"
    faculty = "faculty"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Roll number is only meaningful for students, but is kept optional
    # (nullable) rather than student-only at the table level, so faculty
    # and admin accounts can also be created without one.
    roll_number: Mapped[str | None] = mapped_column(
        String(50), unique=True, nullable=True
    )

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    # Never store or return plaintext passwords -- only the hash.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), nullable=False, default=UserRole.student
    )

    # Storage limit in megabytes. Not enforced yet (file storage is a
    # later phase) but recorded so the schema doesn't need to change
    # when storage is implemented.
    storage_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=1024)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
