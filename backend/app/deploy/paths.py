"""
Safe filesystem path helpers for hosted websites.

Separate namespace from personal file storage (app/storage/paths.py):
websites live under STORAGE_ROOT/websites/, keeping hosted site
content from ever mixing with a student's personal files, per the
Phase 4 storage design (docs/WEBSITE-HOSTING.md).
"""

import uuid
from pathlib import Path

from app.storage.paths import STORAGE_ROOT, ensure_inside_storage_root


def website_storage_dir(user_id: int, website_id: uuid.UUID) -> Path:
    """
    Return the storage directory for one website, creating it if
    needed. Both `user_id` and `website_id` are always trusted,
    server-controlled values (the authenticated user's id and the
    website's own database id) -- never a client-supplied string.
    """
    site_dir = ensure_inside_storage_root(
        STORAGE_ROOT / "websites" / str(int(user_id)) / str(website_id)
    )
    site_dir.mkdir(parents=True, exist_ok=True)
    return site_dir
