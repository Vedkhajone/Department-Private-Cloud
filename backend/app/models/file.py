"""
File ORM model.

Stores metadata only -- never file bytes. Actual file contents live on
the filesystem under app.config.settings.storage_root (see
app/storage/paths.py). `storage_path` here is a server-generated,
opaque on-disk filename -- never a user-supplied path -- used to
locate those bytes. The user-facing `name` column is completely
independent of it, which is what lets a rename update only the
database row without ever touching the filesystem.
"""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class File(Base):
    __tablename__ = "files"
    __table_args__ = (
        # A user cannot have two files with the same name inside the
        # same folder (database-enforced, same reasoning as Folder's
        # equivalent constraint).
        Index(
            "ix_files_user_folder_name",
            "user_id",
            "folder_id",
            "name",
            unique=True,
        ),
        # Covers root-level files (folder_id IS NULL), which the plain
        # unique index above cannot -- see Folder's equivalent index.
        Index(
            "ix_files_user_root_name",
            "user_id",
            "name",
            unique=True,
            postgresql_where=text("folder_id IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # NULL means this file lives at the user's root.
    folder_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("folders.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Server-generated on-disk identifier -- never derived from user
    # input. See app/storage/paths.py.
    storage_path: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
