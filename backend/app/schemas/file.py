"""
Pydantic schemas for file requests/responses.

FileResponse deliberately never includes `storage_path` -- clients
operate on files by database id only, never by filesystem location.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FileRename(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class FileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    folder_id: int | None
    name: str
    size: int
    mime_type: str | None
    created_at: datetime
    updated_at: datetime
