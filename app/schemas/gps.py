import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class LocationPingCreate(BaseModel):
    """Payload schema for GPS location ingestion from driver device."""

    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Latitude in degrees (-90.0 to +90.0)",
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Longitude in degrees (-180.0 to +180.0)",
    )
    recorded_at: datetime = Field(
        ...,
        description="Device timestamp when the GPS coordinate was captured",
    )
    accuracy_meters: Optional[float] = Field(
        None,
        ge=0.0,
        description="Estimated GPS horizontal accuracy in meters (non-negative)",
    )
    speed_mps: Optional[float] = Field(
        None,
        ge=0.0,
        description="Speed over ground in meters per second (non-negative)",
    )
    heading_degrees: Optional[float] = Field(
        None,
        ge=0.0,
        lt=360.0,
        description="Bearing/heading in degrees from true north (0.0 <= heading < 360.0)",
    )


class LocationPingResponse(BaseModel):
    """Response schema for ingested/queried GPS location pings."""

    id: uuid.UUID
    trip_id: uuid.UUID
    driver_id: uuid.UUID
    latitude: float
    longitude: float
    recorded_at: datetime
    received_at: datetime
    accuracy_meters: Optional[float] = None
    speed_mps: Optional[float] = None
    heading_degrees: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LiveLocationResponse(BaseModel):
    """Response schema for latest live location state stored in Redis."""

    trip_id: uuid.UUID
    driver_id: uuid.UUID
    bus_id: uuid.UUID
    latitude: float
    longitude: float
    recorded_at: datetime
    received_at: datetime
    accuracy_meters: Optional[float] = None
    speed_mps: Optional[float] = None
    heading_degrees: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)
