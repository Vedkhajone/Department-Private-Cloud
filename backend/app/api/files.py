"""
File endpoints: upload, list, download, rename, delete.

Every endpoint derives the current user from the JWT (get_current_user)
and every operation on an existing file goes through
app.storage.service, which re-verifies ownership on every call --
a file/folder id supplied by the client is never trusted on its own.
"""

from fastapi import APIRouter, Depends, Query, UploadFile, status
from fastapi import File as UploadFileParam
from fastapi.responses import FileResponse as FastAPIFileResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.file import FileRename, FileResponse
from app.storage import service

router = APIRouter(prefix="/api/files", tags=["files"])


@router.post("/upload", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
def upload_file(
    upload: UploadFile = UploadFileParam(...),
    folder_id: int | None = Query(
        default=None, description="Destination folder id; omit for the root folder"
    ),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.save_uploaded_file(db, user, folder_id, upload)


@router.get("", response_model=list[FileResponse])
def list_files(
    folder_id: int | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_files(db, user, folder_id)


@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    path, file_row = service.resolve_download(db, user, file_id)
    return FastAPIFileResponse(
        path=path,
        filename=file_row.name,
        media_type=file_row.mime_type or "application/octet-stream",
    )


@router.patch("/{file_id}", response_model=FileResponse)
def rename_file(
    file_id: int,
    payload: FileRename,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.rename_file(db, user, file_id, payload.name)


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    file_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    service.delete_file(db, user, file_id)
