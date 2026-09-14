"""
User-facing endpoints that require authentication.
"""

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.user import UserOut

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def read_current_user(user: User = Depends(get_current_user)) -> User:
    return user


@router.get("/staff-only", response_model=UserOut, include_in_schema=True)
def staff_only_example(
    user: User = Depends(require_role(UserRole.faculty, UserRole.admin)),
) -> User:
    """
    Demonstrates role-based access control: only faculty and admin
    accounts may call this endpoint. Students receive a 403. This is
    a placeholder to show the mechanism -- the real faculty/admin API
    is a later phase.
    """
    return user
