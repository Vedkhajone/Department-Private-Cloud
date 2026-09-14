"""
Pydantic schemas for folder requests/responses.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    parent_folder_id: int | None = None


class FolderRename(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class FolderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_folder_id: int | None
    name: str
    created_at: datetime
    updated_at: datetime
