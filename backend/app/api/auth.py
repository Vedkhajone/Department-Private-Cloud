"""
Authentication endpoints: register and login.

Public registration always creates a `student` account -- the `role`
field is never accepted from the request body, so there is no way for
a client to request `faculty` or `admin` through this endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, hash_password, verify_password
from app.config import settings
from app.db.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import TokenResponse, UserLoginRequest, UserOut, UserRegisterRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegisterRequest, db: Session = Depends(get_db)) -> User:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )

    if payload.roll_number:
        existing_roll = (
            db.query(User).filter(User.roll_number == payload.roll_number).first()
        )
        if existing_roll is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this roll number already exists",
            )

    user = User(
        name=payload.name,
        roll_number=payload.roll_number,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.student,  # public registration can never set a role
        storage_limit=settings.default_storage_limit_mb,
    )

    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Guards against a race condition between the check above and
        # the insert (e.g. two simultaneous registrations with the
        # same email/roll number).
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email or roll number already exists",
        )
    db.refresh(user)

    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).first()

    # Use one generic error for both "no such user" and "wrong password"
    # so a client can't use this endpoint to discover which emails are
    # registered.
    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
    )

    if user is None:
        raise invalid_credentials

    if not verify_password(payload.password, user.password_hash):
        raise invalid_credentials

    access_token = create_access_token(
        subject=str(user.id), extra_claims={"role": user.role.value}
    )

    return TokenResponse(access_token=access_token, user=UserOut.model_validate(user))


@router.post("/token", response_model=TokenResponse, include_in_schema=False)
def login_oauth2_form(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> TokenResponse:
    """
    Standard OAuth2 password-flow endpoint (username + password as
    form data). Kept alongside the JSON /login endpoint so the
    interactive API docs' "Authorize" button works out of the box;
    the frontend uses the JSON /login endpoint above.
    """
    user = db.query(User).filter(User.email == form_data.username).first()

    if user is None or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token = create_access_token(
        subject=str(user.id), extra_claims={"role": user.role.value}
    )

    return TokenResponse(access_token=access_token, user=UserOut.model_validate(user))
