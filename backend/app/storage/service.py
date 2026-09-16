"""
Storage business logic: folder/file CRUD, ownership checks, quota
enforcement, and safe file upload/download.

Kept separate from the API routers (app/api/files.py, folders.py,
storage.py) so the routers stay thin HTTP adapters, and this module
can be reasoned about (and tested) independently of FastAPI request
handling -- consistent with the rest of the backend's layering (see
app/auth/security.py vs. app/api/auth.py).

Every function that accepts a folder_id/file_id verifies the row both
exists AND belongs to the given `user` before doing anything with it
-- the caller never needs to (and must never) trust a user_id supplied
by the client. `user` always comes from the `get_current_user` JWT
dependency.
"""

from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.admin.audit import record as record_audit
from app.models.file import File
from app.models.folder import Folder
from app.models.user import User
from app.storage.paths import new_storage_filename, physical_file_path

# Read/write uploads in chunks rather than loading them entirely into
# memory.
_UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MB

_INVALID_NAME_CHARS = set("/\\\x00")


def sanitize_name(raw_name: str) -> str:
    """
    Validate and normalize a user-supplied file/folder display name.

    This name is only ever stored in the database and shown in the UI
    -- it never becomes part of a filesystem path (see
    app/storage/paths.py) -- but it's still validated strictly to keep
    it unambiguous and to reject anything that looks like a path.
    """
    name = (raw_name or "").strip()

    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name cannot be empty")
    if len(name) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name is too long (max 255 characters)",
        )
    if name in (".", ".."):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid name")
    if any(ch in _INVALID_NAME_CHARS for ch in name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name cannot contain '/', '\\', or null characters",
        )

    return name


# ---------------------------------------------------------------------------
# Quota
# ---------------------------------------------------------------------------


def quota_bytes(user: User) -> int:
    """The user's total storage quota in bytes (storage_limit is stored in MB)."""
    return user.storage_limit * 1024 * 1024


def calculate_used_bytes(db: Session, user: User) -> int:
    """
    Sum the size of every file the user owns. Calculating this from
    file metadata on read is acceptable at this phase's scale; a
    running counter/materialized total can be introduced later if it
    becomes a bottleneck.
    """
    total = (
        db.query(func.coalesce(func.sum(File.size), 0)).filter(File.user_id == user.id).scalar()
    )
    return int(total or 0)


# ---------------------------------------------------------------------------
# Folders
# ---------------------------------------------------------------------------


def get_owned_folder(db: Session, user: User, folder_id: int) -> Folder:
    folder = db.query(Folder).filter(Folder.id == folder_id, Folder.user_id == user.id).first()
    if folder is None:
        # Same 404 whether the folder doesn't exist or belongs to
        # someone else -- never reveal which.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    return folder


def _validate_parent(db: Session, user: User, parent_folder_id: int | None) -> None:
    if parent_folder_id is not None:
        get_owned_folder(db, user, parent_folder_id)


def list_folders(db: Session, user: User, parent_folder_id: int | None) -> list[Folder]:
    _validate_parent(db, user, parent_folder_id)
    return (
        db.query(Folder)
        .filter(Folder.user_id == user.id, Folder.parent_folder_id == parent_folder_id)
        .order_by(Folder.name)
        .all()
    )


def create_folder(db: Session, user: User, name: str, parent_folder_id: int | None) -> Folder:
    clean_name = sanitize_name(name)
    _validate_parent(db, user, parent_folder_id)

    duplicate = (
        db.query(Folder)
        .filter(
            Folder.user_id == user.id,
            Folder.parent_folder_id == parent_folder_id,
            Folder.name == clean_name,
        )
        .first()
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A folder with this name already exists here",
        )

    folder = Folder(user_id=user.id, parent_folder_id=parent_folder_id, name=clean_name)
    db.add(folder)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A folder with this name already exists here",
        )
    db.refresh(folder)
    record_audit(
        db, actor_id=user.id, action="folder.create", resource_type="folder",
        resource_id=folder.id, description=f'Created folder "{clean_name}"',
    )
    return folder


def rename_folder(db: Session, user: User, folder_id: int, new_name: str) -> Folder:
    folder = get_owned_folder(db, user, folder_id)
    clean_name = sanitize_name(new_name)

    duplicate = (
        db.query(Folder)
        .filter(
            Folder.user_id == user.id,
            Folder.parent_folder_id == folder.parent_folder_id,
            Folder.name == clean_name,
            Folder.id != folder.id,
        )
        .first()
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A folder with this name already exists here",
        )

    folder.name = clean_name
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A folder with this name already exists here",
        )
    db.refresh(folder)
    return folder


def delete_folder(db: Session, user: User, folder_id: int) -> None:
    folder = get_owned_folder(db, user, folder_id)

    has_subfolder = db.query(Folder.id).filter(Folder.parent_folder_id == folder.id).first()
    has_file = db.query(File.id).filter(File.folder_id == folder.id).first()
    if has_subfolder is not None or has_file is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Folder is not empty. Delete its contents before deleting the folder.",
        )

    folder_id_val, folder_name = folder.id, folder.name
    db.delete(folder)
    db.commit()
    record_audit(
        db, actor_id=user.id, action="folder.delete", resource_type="folder",
        resource_id=folder_id_val, description=f'Deleted folder "{folder_name}"',
    )


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------


def get_owned_file(db: Session, user: User, file_id: int) -> File:
    file_row = db.query(File).filter(File.id == file_id, File.user_id == user.id).first()
    if file_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return file_row


def list_files(db: Session, user: User, folder_id: int | None) -> list[File]:
    if folder_id is not None:
        get_owned_folder(db, user, folder_id)
    return (
        db.query(File)
        .filter(File.user_id == user.id, File.folder_id == folder_id)
        .order_by(File.name)
        .all()
    )


def save_uploaded_file(
    db: Session, user: User, folder_id: int | None, upload: UploadFile
) -> File:
    """
    Save an uploaded file to disk and record its metadata.

    Order of operations matters here:
      1. Validate everything we can before touching the filesystem
         (folder ownership, name, quota headroom).
      2. Stream the upload to disk, aborting if it would exceed the
         user's remaining quota mid-stream.
      3. Insert the metadata row.
      4. If anything from step 2 onward fails, delete the (possibly
         partial) physical file so we never leave an orphaned file with
         no matching database row, or a database row with no file.
    """
    if folder_id is not None:
        get_owned_folder(db, user, folder_id)

    display_name = sanitize_name(upload.filename or "untitled")

    duplicate = (
        db.query(File)
        .filter(File.user_id == user.id, File.folder_id == folder_id, File.name == display_name)
        .first()
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A file with this name already exists here",
        )

    remaining = quota_bytes(user) - calculate_used_bytes(db, user)
    if remaining <= 0:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Storage quota exceeded",
        )

    storage_filename = new_storage_filename()
    dest_path = physical_file_path(user.id, storage_filename)

    bytes_written = 0
    try:
        with open(dest_path, "wb") as out:
            while True:
                chunk = upload.file.read(_UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > remaining:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Storage quota exceeded",
                    )
                out.write(chunk)
    except Exception:
        dest_path.unlink(missing_ok=True)
        raise

    file_row = File(
        user_id=user.id,
        folder_id=folder_id,
        name=display_name,
        storage_path=storage_filename,
        size=bytes_written,
        mime_type=upload.content_type,
    )
    db.add(file_row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        dest_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A file with this name already exists here",
        )
    except Exception:
        db.rollback()
        dest_path.unlink(missing_ok=True)
        raise

    db.refresh(file_row)
    record_audit(
        db, actor_id=user.id, action="file.upload", resource_type="file",
        resource_id=file_row.id, description=f'Uploaded file "{display_name}" ({bytes_written} bytes)',
    )
    return file_row


def resolve_download(db: Session, user: User, file_id: int) -> tuple[Path, File]:
    file_row = get_owned_file(db, user, file_id)
    path = physical_file_path(user.id, file_row.storage_path)
    if not path.is_file():
        # Metadata exists but the physical file is missing -- treat it
        # the same as "not found" rather than leaking the discrepancy.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return path, file_row


def rename_file(db: Session, user: User, file_id: int, new_name: str) -> File:
    file_row = get_owned_file(db, user, file_id)
    clean_name = sanitize_name(new_name)

    duplicate = (
        db.query(File)
        .filter(
            File.user_id == user.id,
            File.folder_id == file_row.folder_id,
            File.name == clean_name,
            File.id != file_row.id,
        )
        .first()
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A file with this name already exists here",
        )

    # The on-disk filename is a server-generated identifier, entirely
    # independent of the display name (see app/storage/paths.py), so
    # renaming never touches the filesystem -- only this column.
    file_row.name = clean_name
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A file with this name already exists here",
        )
    db.refresh(file_row)
    return file_row


def delete_file(db: Session, user: User, file_id: int) -> None:
    file_row = get_owned_file(db, user, file_id)
    path = physical_file_path(user.id, file_row.storage_path)

    # Delete the database row first: if the physical delete below
    # fails partway, the result is an orphaned file on disk (harmless,
    # cleanable later) rather than a database row pointing at a file
    # that no longer exists (which would break downloads).
    file_id_val, file_name = file_row.id, file_row.name
    db.delete(file_row)
    db.commit()

    path.unlink(missing_ok=True)
    record_audit(
        db, actor_id=user.id, action="file.delete", resource_type="file",
        resource_id=file_id_val, description=f'Deleted file "{file_name}"',
    )
