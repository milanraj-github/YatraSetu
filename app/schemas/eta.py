import uuid
from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict, Field


class StopETAResponse(BaseModel):
    """Estimated arrival time information for a specific route stop."""

    stop_id: uuid.UUID = Field(
        ...,
        description="Unique identifier of the RouteStop association record",
    )
    stop_order: int = Field(
        ...,
        description="Sequential order of the stop along the route (1-based)",
    )
    boarding_point_id: uuid.UUID = Field(
        ...,
        description="Unique identifier of the associated BoardingPoint",
    )
    boarding_point_name: str = Field(
        ...,
        description="Name of the boarding point stop",
    )
    latitude: float = Field(
        ...,
        description="Latitude of the boarding point",
    )
    longitude: float = Field(
        ...,
        description="Longitude of the boarding point",
    )
    distance_meters: float = Field(
        ...,
        description="Geodesic / PostGIS distance in meters from current bus location to this stop",
    )
    eta_seconds: float = Field(
        ...,
        description="Estimated travel duration in seconds based on configured baseline speed",
    )
    estimated_arrival_at: datetime = Field(
        ...,
        description="Projected UTC timestamp of arrival at this stop",
    )

    model_config = ConfigDict(from_attributes=True)


class TripETAResponse(BaseModel):
    """Estimated arrival times across all stops for an active trip."""

    trip_id: uuid.UUID = Field(
        ...,
        description="Unique identifier of the trip",
    )
    generated_at: datetime = Field(
        ...,
        description="UTC timestamp when this ETA evaluation was generated",
    )
    current_latitude: float = Field(
        ...,
        description="Current live latitude of the operating bus",
    )
    current_longitude: float = Field(
        ...,
        description="Current live longitude of the operating bus",
    )
    stops: List[StopETAResponse] = Field(
        default_factory=list,
        description="Ordered list of route stops with distance and arrival time estimates",
    )

    model_config = ConfigDict(from_attributes=True)
