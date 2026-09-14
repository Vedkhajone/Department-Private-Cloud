"""
Pydantic schemas for user-related API requests and responses.

Kept separate from app/models/user.py: models describe the database
table, schemas describe what the API accepts and returns. In
particular, UserOut never includes password_hash.
"""

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserRegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    roll_number: str | None = Field(default=None, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    """Safe user representation -- never includes password_hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    roll_number: str | None
    email: EmailStr
    role: UserRole
    storage_limit: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
