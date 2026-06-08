from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import UserRole


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError("invalid email")
    return email


class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    role: UserRole = UserRole.VIEWER
    is_active: bool = True

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    email: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: UserRole | None = None
    is_active: bool | None = None

    @field_validator("email")
    @classmethod
    def validate_optional_email(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return normalize_email(value)


class UserActivationUpdate(BaseModel):
    is_active: bool


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
