import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TripStatus


class TripCreate(BaseModel):
    """Schema for scheduling a new trip."""

    route_id: uuid.UUID = Field(..., description="ID of the route to be executed")
    bus_id: uuid.UUID = Field(..., description="ID of the bus assigned to the trip")
    driver_id: uuid.UUID = Field(..., description="ID of the driver assigned to the trip")
    scheduled_start_at: Optional[datetime] = Field(
        None, description="Optional scheduled start timestamp"
    )


class TripResponse(BaseModel):
    """Response schema for trip details."""

    id: uuid.UUID
    route_id: uuid.UUID
    bus_id: uuid.UUID
    driver_id: uuid.UUID
    status: TripStatus
    scheduled_start_at: Optional[datetime] = None
    actual_start_at: Optional[datetime] = None
    actual_end_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
