"""
Pydantic schemas for Buses, Routes, Stops, Drivers, Schedules, and Trips.
Used by Phase 2 admin management endpoints.
"""
import enum
from datetime import datetime, time, date
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


# ──────────────────────────────────────────────────────────────────────────────
# Bus Schemas
# ──────────────────────────────────────────────────────────────────────────────

class BusStatusEnum(str, enum.Enum):
    IDLE = "IDLE"
    IN_TRIP = "IN_TRIP"
    MAINTENANCE = "MAINTENANCE"
    INACTIVE = "INACTIVE"


class BusCreate(BaseModel):
    bus_number: str = Field(..., min_length=1, max_length=30, json_schema_extra={"example": "BUS-04"})
    registration_number: str = Field(..., min_length=1, max_length=50, json_schema_extra={"example": "KA-19-AB-1234"})
    capacity: int = Field(default=50, ge=1, le=200)
    route_id: Optional[int] = None


class BusUpdate(BaseModel):
    capacity: Optional[int] = Field(default=None, ge=1, le=200)
    status: Optional[BusStatusEnum] = None
    route_id: Optional[int] = None

class BusRouteSummary(BaseModel):
    id: int
    name: str
    code: str
    model_config = ConfigDict(from_attributes=True)

class BusResponse(BaseModel):
    id: int
    bus_number: str
    registration_number: str
    capacity: int
    status: BusStatusEnum
    route_id: Optional[int] = None
    route: Optional[BusRouteSummary] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────────────────────
# Boarding Point / Stop Schemas
# ──────────────────────────────────────────────────────────────────────────────

class BoardingPointCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, json_schema_extra={"example": "Udupi Bus Stand"})
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    radius_meters: int = Field(default=100, ge=10, le=1000)


class BoardingPointUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    radius_meters: Optional[int] = Field(default=None, ge=10, le=1000)


class BoardingPointResponse(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float
    radius_meters: int

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────────────────────
# Route Schemas
# ──────────────────────────────────────────────────────────────────────────────

class RouteDirectionEnum(str, enum.Enum):
    MORNING = "MORNING"
    EVENING = "EVENING"


class RouteStopInput(BaseModel):
    boarding_point_id: int
    sequence_order: int = Field(..., ge=1)
    direction: RouteDirectionEnum


class RouteCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, json_schema_extra={"example": "Udupi-SMVITM Route"})
    code: str = Field(..., min_length=1, max_length=30, json_schema_extra={"example": "RT-01"})
    stops: Optional[List[RouteStopInput]] = []


class RouteUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)


class RouteStopResponse(BaseModel):
    id: int
    boarding_point_id: int
    sequence_order: int
    direction: RouteDirectionEnum
    boarding_point: BoardingPointResponse

    model_config = ConfigDict(from_attributes=True)


class RouteResponse(BaseModel):
    id: int
    name: str
    code: str
    stops: List[RouteStopResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────────────────────
# Driver Management Schemas
# ──────────────────────────────────────────────────────────────────────────────

class DriverResponse(BaseModel):
    id: int
    firebase_uid: str
    email: str
    full_name: str
    is_email_verified: bool
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssignmentStatusEnum(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class AssignBusRequest(BaseModel):
    bus_id: int
    assigned_until: Optional[datetime] = None


class DriverAssignmentResponse(BaseModel):
    id: int
    driver_id: int
    bus_id: int
    status: AssignmentStatusEnum
    assigned_from: datetime
    assigned_until: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────────────────────
# Schedule Schemas
# ──────────────────────────────────────────────────────────────────────────────

class ScheduleCreate(BaseModel):
    bus_id: int
    route_id: int
    start_time: time = Field(..., json_schema_extra={"example": "07:35:00"})
    end_time: time = Field(..., json_schema_extra={"example": "09:10:00"})
    direction: RouteDirectionEnum
    days_of_week: str = Field(
        default="MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY,SATURDAY",
        example="MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY,SATURDAY"
    )


class ScheduleUpdate(BaseModel):
    bus_id: Optional[int] = None
    route_id: Optional[int] = None
    direction: Optional[RouteDirectionEnum] = None

    start_time: Optional[time] = None
    end_time: Optional[time] = None
    days_of_week: Optional[str] = None
    active: Optional[bool] = None


class ScheduleResponse(BaseModel):
    id: int
    bus_id: int
    route_id: int
    start_time: time
    end_time: time
    direction: RouteDirectionEnum
    days_of_week: str
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────────────────────
# Trip / Tracking Session Schemas
# ──────────────────────────────────────────────────────────────────────────────

class SessionStatusEnum(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class TripResponse(BaseModel):
    id: int
    bus_id: int
    route_id: int
    schedule_id: int
    driver_id: int
    session_date: date
    direction: RouteDirectionEnum
    status: SessionStatusEnum
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
