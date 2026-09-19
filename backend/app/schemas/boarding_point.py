import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class BoardingPointBase(BaseModel):
    """Base schema for BoardingPoint entity."""

    name: str = Field(..., min_length=1, max_length=100, description="Boarding point / stop name")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Geographical latitude (-90 to 90)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Geographical longitude (-180 to 180)")
    address: Optional[str] = Field(None, max_length=255, description="Street address or landmark")
    is_active: bool = Field(default=True, description="Active status of the boarding point")

    @field_validator("name", mode="before")
    @classmethod
    def strip_and_validate_non_empty(cls, value: str) -> str:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Name cannot be blank or whitespace only")
            return stripped
        return value


class BoardingPointCreate(BoardingPointBase):
    """Schema for creating a new boarding point."""

    pass


class BoardingPointUpdate(BaseModel):
    """Schema for updating an existing boarding point."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    address: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None

    @field_validator("name", mode="before")
    @classmethod
    def strip_optional_name(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Name cannot be blank or whitespace only")
            return stripped
        return value


class BoardingPointResponse(BoardingPointBase):
    """Response schema for boarding point details."""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
