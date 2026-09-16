"""
Website management endpoints -- all require authentication, and every
operation on an existing website re-verifies ownership via
app.deploy.service.get_owned_website (id + owner_id in one query, so
there's no separate "fetch, then check" step to forget).

Deployment (POST /api/websites) never accepts an owner id from the
client -- the owner is always the authenticated user from the JWT.
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.deploy import service
from app.models.user import User
from app.schemas.website import WebsiteLogsResponse, WebsiteResponse

router = APIRouter(prefix="/api/websites", tags=["websites"])


@router.post("", response_model=WebsiteResponse, status_code=status.HTTP_201_CREATED)
def deploy_website(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    upload: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.deploy_website(db, user, name, upload, background_tasks)


@router.get("", response_model=list[WebsiteResponse])
def list_my_websites(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return service.list_websites(db, user)


@router.get("/{website_id}", response_model=WebsiteResponse)
def get_website(
    website_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.get_owned_website(db, user, website_id)


@router.delete("/{website_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_website(
    website_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    service.delete_website(db, user, website_id)


@router.post("/{website_id}/start", response_model=WebsiteResponse)
def start_website(
    website_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.start_website(db, user, website_id)


@router.post("/{website_id}/stop", response_model=WebsiteResponse)
def stop_website(
    website_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.stop_website(db, user, website_id)


@router.post("/{website_id}/restart", response_model=WebsiteResponse)
def restart_website(
    website_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.restart_website(db, user, website_id)


@router.get("/{website_id}/logs", response_model=WebsiteLogsResponse)
def get_website_logs(
    website_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return WebsiteLogsResponse(logs=service.get_website_logs(db, user, website_id))
