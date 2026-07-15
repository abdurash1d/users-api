import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.users.models import Role


class UserRead(BaseModel):
    """Public representation of a user."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    first_name: str | None
    last_name: str | None
    role: Role
    is_verified: bool
    created_at: datetime


class UserUpdate(BaseModel):
    """Partial update payload. `role` and `is_verified` are admin-only."""

    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    password: str | None = Field(None, min_length=8, max_length=128)
    role: Role | None = None
    is_verified: bool | None = None
