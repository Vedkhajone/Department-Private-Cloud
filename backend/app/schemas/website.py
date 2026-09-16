"""
Pydantic schemas for website requests/responses.

There is no WebsiteCreate JSON schema -- the deploy endpoint accepts
multipart/form-data (a name field plus a ZIP file), not JSON, so its
parameters are declared directly on the route (see app/api/websites.py).
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.website import WebsiteFramework, WebsiteStatus, WebsiteType


class WebsiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    type: WebsiteType
    framework: WebsiteFramework
    status: WebsiteStatus
    public_url: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class WebsiteLogsResponse(BaseModel):
    logs: str
