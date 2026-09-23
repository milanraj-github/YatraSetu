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
    model_config = ConfigDict(from_attributes=True)

class RouteStopSummarySchema(BaseModel):
    id: int
    name: str
    sequence_order: int
    latitude: float
    longitude: float
    model_config = ConfigDict(from_attributes=True)

class RouteSummarySchema(BaseModel):
    id: int
    name: str
    code: str
    direction: RouteDirection
    stops: List[RouteStopSummarySchema] = []
    model_config = ConfigDict(from_attributes=True)

class ScheduleSummarySchema(BaseModel):
    id: int
    start_time: time
    end_time: time
    direction: RouteDirection
    model_config = ConfigDict(from_attributes=True)

class SessionSummarySchema(BaseModel):
    id: int
    status: SessionStatus
    direction: RouteDirection
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class DriverTrackingStatusResponse(BaseModel):
    tracking_active: bool
    bus: Optional[BusSummarySchema] = None
    session: Optional[SessionSummarySchema] = None
    route: Optional[RouteSummarySchema] = None
    schedule: Optional[ScheduleSummarySchema] = None

class LiveTripResponse(BaseModel):
    trip_id: int
    bus_id: int
    route_id: Optional[int] = None
    route_name: Optional[str] = None

    bus_number: str
    status: SessionStatus
    location_status: str
    deviation_status: str = "ON_ROUTE"
    accident_alert_id: int | None = None
    accident_deadline_at: str | None = None
    accident_status: str | None = None
    active_sos_id: int | None = None  # LIVE, LAST_KNOWN_LOCATION, GPS_NOT_AVAILABLE
    location: Optional[LocationPointSchema] = None

class ActiveBusTrackingItem(BaseModel):
    trip_id: int
    bus_id: int
    route_id: Optional[int] = None
    route_name: Optional[str] = None

    bus_number: str
    registration_number: str
    status: SessionStatus
    direction: RouteDirection
    driver_name: str
    location_status: str
    deviation_status: str = "ON_ROUTE"
    accident_alert_id: int | None = None
    accident_deadline_at: str | None = None
    accident_status: str | None = None
    active_sos_id: int | None = None  # LIVE, LAST_KNOWN_LOCATION, GPS_NOT_AVAILABLE
    location: Optional[LocationPointSchema] = None


class GpsBatchIngestRequest(BaseModel):
    locations: List[GpsIngestRequest]

class GpsBatchIngestResponse(BaseModel):
    accepted: int
    duplicates: int
    rejected: int
    failed_points: List[str]  # Just ISO timestamps of failed/rejected points so client can remove or keep
    synced_points: List[str]  # ISO timestamps of successfully synced or ignored duplicate points

class StopIntelligenceStopSchema(BaseModel):
    id: int
    name: str
    sequence_order: int

class StopIntelligenceResponse(BaseModel):
    current_stop: Optional[StopIntelligenceStopSchema] = None
    next_stop: Optional[StopIntelligenceStopSchema] = None
    status: str
    deviation_status: str = "ON_ROUTE"
    accident_alert_id: int | None = None
    accident_deadline_at: str | None = None
    accident_status: str | None = None
    active_sos_id: int | None = None
