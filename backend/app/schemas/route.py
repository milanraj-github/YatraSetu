import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class RouteBase(BaseModel):
    """Base schema for Route entity."""

    name: str = Field(..., min_length=1, max_length=100, description="Descriptive route name")
    code: str = Field(..., min_length=1, max_length=50, description="Unique route code identifier")
    description: Optional[str] = Field(None, max_length=255, description="Optional route description")
    is_active: bool = Field(default=True, description="Active status of the route")

    @field_validator("name", "code", mode="before")
    @classmethod
    def strip_and_validate_non_empty(cls, value: str) -> str:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Value cannot be blank or whitespace only")
            return stripped
        return value


class RouteCreate(RouteBase):
    """Schema for creating a new route."""

    pass


class RouteUpdate(BaseModel):
    """Schema for updating an existing route."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None

    @field_validator("name", "code", mode="before")
    @classmethod
    def strip_optional_string(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Value cannot be blank or whitespace only")
            return stripped
        return value


class RouteResponse(RouteBase):
    """Response schema for route details."""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
