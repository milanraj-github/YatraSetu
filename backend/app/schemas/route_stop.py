import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.boarding_point import BoardingPointResponse


class RouteStopBase(BaseModel):
    """Base schema for RouteStop entity."""

    boarding_point_id: uuid.UUID = Field(..., description="ID of the associated boarding point")
    stop_order: int = Field(..., gt=0, description="Sequential sequence position of the stop (1, 2, ...)")
    scheduled_arrival_offset_minutes: Optional[int] = Field(
        default=0, ge=0, description="Scheduled arrival offset in minutes from route start"
    )


class RouteStopCreate(RouteStopBase):
    """Schema for adding a new stop to a route."""

    pass


class RouteStopUpdate(BaseModel):
    """Schema for updating a route stop's arrival offset."""

    scheduled_arrival_offset_minutes: Optional[int] = Field(
        None, ge=0, description="Updated scheduled arrival offset in minutes"
    )


class RouteStopOrderUpdate(BaseModel):
    """Schema for updating a route stop's order in the sequence."""

    new_stop_order: int = Field(..., gt=0, description="New positive stop sequence position")


class RouteStopResponse(BaseModel):
    """Response schema for route stop with embedded boarding point details."""

    id: uuid.UUID
    route_id: uuid.UUID
    boarding_point_id: uuid.UUID
    stop_order: int
    scheduled_arrival_offset_minutes: Optional[int]
    created_at: datetime
    boarding_point: Optional[BoardingPointResponse] = None

    model_config = ConfigDict(from_attributes=True)
