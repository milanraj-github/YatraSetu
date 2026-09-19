import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator

from app.models.enums import ParentLinkStatus, UserRole
from app.schemas.user import STUDENT_EMAIL_DOMAIN, validate_student_domain


class ParentRegisterRequest(BaseModel):
    """Payload for registering a parent account linked to a student."""

    email: EmailStr
    full_name: str
    child_email: EmailStr

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Full name cannot be empty")
        return v.strip()

    @model_validator(mode="after")
    def validate_child_domain(self) -> "ParentRegisterRequest":
        validate_student_domain(self.child_email, UserRole.STUDENT)
        return self


class ParentLinkRequestResponse(BaseModel):
    """Response schema for a parent-child link request."""

    id: uuid.UUID
    parent_id: uuid.UUID
    student_id: uuid.UUID
    status: ParentLinkStatus
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    parent_email: Optional[EmailStr] = None
    parent_name: Optional[str] = None
    student_email: Optional[EmailStr] = None
    student_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ParentChildResponse(BaseModel):
    """Response schema for an approved linked child."""

    id: uuid.UUID
    student_id: uuid.UUID
    student_name: str
    student_email: EmailStr
    assigned_bus_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
