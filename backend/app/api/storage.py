"""
Aggregate storage usage endpoint.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.storage import StorageUsageResponse
from app.storage import service

router = APIRouter(prefix="/api/storage", tags=["storage"])


@router.get("/usage", response_model=StorageUsageResponse)
def get_storage_usage(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StorageUsageResponse:
    quota = service.quota_bytes(user)
    used = service.calculate_used_bytes(db, user)
    return StorageUsageResponse(
        quota_bytes=quota,
        used_bytes=used,
        available_bytes=max(quota - used, 0),
    )
