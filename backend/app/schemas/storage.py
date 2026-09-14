"""
Pydantic schema for the storage usage summary endpoint.
"""

from pydantic import BaseModel


class StorageUsageResponse(BaseModel):
    quota_bytes: int
    used_bytes: int
    available_bytes: int
