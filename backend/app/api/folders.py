"""
Folder endpoints. Folders are a logical grouping of a user's files --
see app/storage/service.py and app/models/folder.py for the details.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.models.folder import Folder
from app.models.user import User
from app.schemas.folder import FolderCreate, FolderRename, FolderResponse
from app.storage import service

router = APIRouter(prefix="/api/folders", tags=["folders"])


@router.post("", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
def create_folder(
    payload: FolderCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Folder:
    return service.create_folder(db, user, payload.name, payload.parent_folder_id)


@router.get("", response_model=list[FolderResponse])
def list_folders(
    parent_folder_id: int | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Folder]:
    return service.list_folders(db, user, parent_folder_id)


@router.patch("/{folder_id}", response_model=FolderResponse)
def rename_folder(
    folder_id: int,
    payload: FolderRename,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Folder:
    return service.rename_folder(db, user, folder_id, payload.name)


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder(
    folder_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    service.delete_folder(db, user, folder_id)
