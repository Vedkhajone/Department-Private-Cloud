"""
Password hashing and JWT creation/verification.

Password flow:
    plaintext password -> hash_password() -> password_hash (stored in DB)
    plaintext password + stored hash -> verify_password() -> bool

Passwords are hashed with Argon2 via pwdlib. Argon2 is a modern,
memory-hard hashing algorithm -- a good default for new applications.
Plaintext passwords are never stored or logged anywhere.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.config import settings

password_hasher = PasswordHash.recommended()


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password for storage. Never store the plaintext."""
    return password_hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Check a plaintext password against a stored hash."""
    return password_hasher.verify(plain_password, password_hash)


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """
    Create a signed JWT for the given subject (the user id, as a string).

    The token embeds:
      - sub: the user id, used to identify the user on later requests
      - role: the user's role, so role checks don't require a DB hit
      - exp: expiry, enforced automatically on decode
    """
    if not settings.jwt_secret:
        raise RuntimeError(
            "JWT_SECRET is not configured. Set it in the environment before "
            "issuing tokens."
        )

    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expire,
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT. Raises jwt.PyJWTError (or a subclass,
    e.g. ExpiredSignatureError, InvalidTokenError) on any problem --
    the caller (the auth dependency) is responsible for turning that
    into an HTTP 401 response.
    """
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
