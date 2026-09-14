"""
Reusable FastAPI authentication/authorization dependencies.

get_current_user:
    1. Extracts the bearer token (via OAuth2PasswordBearer).
    2. Validates and decodes it.
    3. Loads the corresponding user from the database.
    4. Rejects missing/invalid/expired tokens or unknown users with 401.

require_role:
    Builds a dependency that additionally rejects users whose role is
    not in the allowed set, with 403.
"""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.db.database import get_db
from app.models.user import User, UserRole

# tokenUrl points at the OAuth2 form-based login endpoint, used only
# for OpenAPI docs (the "Authorize" button) -- it doesn't change how
# tokens are read from actual requests.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        raise credentials_error

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_error

    try:
        user = db.get(User, int(user_id))
    except (TypeError, ValueError):
        raise credentials_error

    if user is None:
        raise credentials_error

    return user


def require_role(*allowed_roles: UserRole):
    """
    Dependency factory for role-based access control.

    Usage:
        @router.get("/faculty-only")
        def endpoint(user: User = Depends(require_role(UserRole.faculty, UserRole.admin))):
            ...
    """

    def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return user

    return role_checker
