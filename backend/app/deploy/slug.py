"""
URL-safe slug generation for websites.

A slug is always derived server-side from the website's display name
-- a client can never supply one directly, which is what guarantees it
can't be used for path traversal or to collide with a route the app
defines (e.g. "api").
"""

import re
import secrets

from sqlalchemy.orm import Session

from app.models.website import Website

_NON_SLUG_CHARS = re.compile(r"[^a-z0-9]+")

# Slugs double as URL path segments (/sites/<slug>, /apps/<slug>) --
# never allow one to collide with another route prefix the app owns.
_RESERVED_SLUGS = {"api", "sites", "apps", "static", "assets"}


def slugify(name: str) -> str:
    base = _NON_SLUG_CHARS.sub("-", name.strip().lower()).strip("-")
    return base or "site"


def generate_unique_slug(db: Session, name: str) -> str:
    base = slugify(name)[:60]
    if base in _RESERVED_SLUGS:
        base = f"{base}-site"

    slug = base
    while db.query(Website.id).filter(Website.slug == slug).first() is not None:
        slug = f"{base}-{secrets.token_hex(3)}"
    return slug
