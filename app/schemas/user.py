import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator

from app.models.enums import UserRole

STUDENT_EMAIL_DOMAIN = "sode-edu.in"


def validate_student_domain(email: str, role: UserRole) -> None:
    """Validate that students use the mandatory college email domain."""
    if role == UserRole.STUDENT:
        domain = email.split("@")[-1].lower() if "@" in email else ""
        if domain != STUDENT_EMAIL_DOMAIN.lower():
            raise ValueError(
                f"Student email must use the @{STUDENT_EMAIL_DOMAIN} domain"
            )


class UserBase(BaseModel):
    """Base schema for user identity."""

    email: EmailStr
    full_name: str
    role: UserRole


class UserCreate(UserBase):
    """Schema for registering or synchronizing a user from Firebase."""

    firebase_uid: str

    @model_validator(mode="after")
    def check_student_domain(self) -> "UserCreate":
        validate_student_domain(self.email, self.role)
        return self


class UserResponse(BaseModel):
    """Response schema for authenticated user."""

    id: uuid.UUID
    firebase_uid: str
    email: EmailStr
    full_name: str
    role: UserRole
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
