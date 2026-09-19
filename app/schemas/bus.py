import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class BusBase(BaseModel):
    """Base schema for bus entity data."""

    bus_number: str = Field(..., min_length=1, max_length=50, description="Bus identification number")
    registration_number: str = Field(..., min_length=1, max_length=50, description="Vehicle registration plate number")
    capacity: int = Field(..., gt=0, description="Total seating capacity (must be greater than 0)")
    is_active: bool = Field(default=True, description="Active status of the bus")

    @field_validator("bus_number", "registration_number", mode="before")
    @classmethod
    def strip_and_validate_non_empty(cls, value: str) -> str:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Value cannot be blank or whitespace only")
            return stripped
        return value


class BusCreate(BusBase):
    """Schema for creating a new bus."""

    pass


class BusUpdate(BaseModel):
    """Schema for updating an existing bus."""

    bus_number: Optional[str] = Field(None, min_length=1, max_length=50)
    registration_number: Optional[str] = Field(None, min_length=1, max_length=50)
    capacity: Optional[int] = Field(None, gt=0)
    is_active: Optional[bool] = None

    @field_validator("bus_number", "registration_number", mode="before")
    @classmethod
    def strip_optional_string(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Value cannot be blank or whitespace only")
            return stripped
        return value


class BusResponse(BusBase):
    """Response schema for bus details."""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
