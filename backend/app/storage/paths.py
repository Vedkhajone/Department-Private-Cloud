"""
Safe filesystem path helpers for user storage.

The golden rule: no path component derived from user input (a file or
folder *display name*) is ever used to build a filesystem path. Only
server-generated identifiers touch the filesystem:

  - the user's numeric id, which comes from the authenticated JWT/
    database -- never from a client-supplied string, and
  - a random UUID generated on the server for every uploaded file.

Folder hierarchy is a purely logical/database concept (see
app/models/folder.py) -- it has no mirror on disk. Every physical file
lives directly under the owning user's flat storage directory, which
means a folder rename/move never requires touching the filesystem, and
there is no folder-name-derived path for an attacker to manipulate in
the first place.
"""

import uuid
from pathlib import Path

from app.config import settings

STORAGE_ROOT = Path(settings.storage_root).resolve()


def ensure_inside_storage_root(path: Path) -> Path:
    """Raise if `path` does not resolve to somewhere inside STORAGE_ROOT."""
    resolved = path.resolve()
    if resolved != STORAGE_ROOT and STORAGE_ROOT not in resolved.parents:
        raise ValueError(f"Resolved path '{resolved}' escaped STORAGE_ROOT")
    return resolved


def user_storage_dir(user_id: int) -> Path:
    """
    Return the storage directory for one user, creating it if needed.

    `user_id` is always a trusted integer (the authenticated user's
    database id) -- never a client-supplied string -- so this cannot be
    used for path traversal. The containment check is still applied as
    defense in depth.
    """
    user_dir = ensure_inside_storage_root(STORAGE_ROOT / "users" / str(int(user_id)))
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def new_storage_filename() -> str:
    """
    A random, server-generated on-disk filename for a newly uploaded
    file. Never derived from the user-supplied filename, so it cannot
    be used for path traversal and cannot collide with another file.
    """
    return uuid.uuid4().hex


def physical_file_path(user_id: int, storage_filename: str) -> Path:
    """
    Resolve the on-disk path for a stored file. Guaranteed to live
    directly inside the owning user's storage directory.
    """
    user_dir = user_storage_dir(user_id)
    path = ensure_inside_storage_root(user_dir / storage_filename)

    if path.parent != user_dir:
        # storage_filename is always a bare uuid4 hex string with no
        # path separators, but this guards against that assumption
        # ever being violated.
        raise ValueError("Resolved file path escaped the user's storage directory")

    return path
