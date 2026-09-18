from datetime import datetime, time
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from app.models.route import RouteDirection
from app.models.schedule import SessionStatus
from app.models.bus import BusStatus

class GpsIngestRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude between -90 and 90")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude between -180 and 180")
    speed: float = Field(default=0.0, ge=0.0, description="Speed in km/h")
    heading: float = Field(default=0.0, ge=0.0, le=360.0, description="Heading in degrees")
    accuracy: float = Field(default=0.0, ge=0.0, description="Accuracy radius in meters")
    recorded_at: datetime = Field(..., description="Device sensor timestamp in UTC")
    
    # Client MUST NOT send bus_id or driver_id. Determined strictly by backend!

class LocationPointSchema(BaseModel):
    latitude: float
    longitude: float
    speed: float
    heading: float
    accuracy: float
    recorded_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class BusSummarySchema(BaseModel):
    id: int
    bus_number: str
    registration_number: str
    status: BusStatus

class RouteStopSummarySchema(BaseModel):
    id: int
    name: str
    sequence_order: int
    latitude: float
    longitude: float

class RouteSummarySchema(BaseModel):
    id: int
    name: str
    code: str
    direction: RouteDirection
    stops: List[RouteStopSummarySchema] = []

class ScheduleSummarySchema(BaseModel):
    id: int
    start_time: str
    end_time: str
    direction: RouteDirection

class SessionSummarySchema(BaseModel):
    id: int
    status: SessionStatus
    direction: RouteDirection
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

class DriverTrackingStatusResponse(BaseModel):
    tracking_active: bool
    bus: Optional[BusSummarySchema] = None
    session: Optional[SessionSummarySchema] = None
    route: Optional[RouteSummarySchema] = None
    schedule: Optional[ScheduleSummarySchema] = None

class LiveTripResponse(BaseModel):
    trip_id: int
    bus_id: int
    bus_number: str
    status: SessionStatus
    location_status: str  # LIVE, LAST_KNOWN_LOCATION, GPS_NOT_AVAILABLE
    location: Optional[LocationPointSchema] = None

class ActiveBusTrackingItem(BaseModel):
    trip_id: int
    bus_id: int
    bus_number: str
    registration_number: str
    status: SessionStatus
    direction: RouteDirection
    driver_name: str
    location_status: str  # LIVE, LAST_KNOWN_LOCATION, GPS_NOT_AVAILABLE
    location: Optional[LocationPointSchema] = None
