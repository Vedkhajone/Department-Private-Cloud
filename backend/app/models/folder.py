"""
Folder ORM model.

Folders are a purely logical/database concept used to organize a
user's files -- there is no matching directory on disk. Physical files
always live in a flat, per-user directory (see app/storage/paths.py);
folder membership is tracked only through File.folder_id and
Folder.parent_folder_id.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Folder(Base):
    __tablename__ = "folders"
    __table_args__ = (
        # A user cannot have two folders with the same name inside the
        # same parent folder (enforced at the database level, not just
        # in application code, so a race between two requests can't
        # create a duplicate).
        Index(
            "ix_folders_user_parent_name",
            "user_id",
            "parent_folder_id",
            "name",
            unique=True,
        ),
        # The constraint above doesn't cover root-level folders --
        # SQL treats every NULL as distinct, so two rows with the same
        # (user_id, name) and parent_folder_id IS NULL would not
        # collide under a plain unique index. This partial index
        # covers that case specifically.
        Index(
            "ix_folders_user_root_name",
            "user_id",
            "name",
            unique=True,
            postgresql_where=text("parent_folder_id IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # NULL means this folder lives at the user's root.
    parent_folder_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("folders.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
