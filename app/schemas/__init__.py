"""Schemas package for request/response serialization."""
from app.schemas.boarding_point import (
    BoardingPointBase,
    BoardingPointCreate,
    BoardingPointResponse,
    BoardingPointUpdate,
)
from app.schemas.bus import BusBase, BusCreate, BusResponse, BusUpdate
from app.schemas.driver import DriverAssignmentResponse
from app.schemas.gps import (
    GPSBatchSyncRequest,
    GPSBatchSyncResponse,
    GPSPointSyncItem,
    LiveLocationResponse,
    LocationPingCreate,
    LocationPingResponse,
)
from app.schemas.eta import StopETAResponse, TripETAResponse
from app.schemas.parent_child import (
    ParentChildResponse,
    ParentLinkRequestResponse,
    ParentRegisterRequest,
)
from app.schemas.route import RouteBase, RouteCreate, RouteResponse, RouteUpdate
from app.schemas.route_stop import (
    RouteStopBase,
    RouteStopCreate,
    RouteStopOrderUpdate,
    RouteStopResponse,
    RouteStopUpdate,
)
from app.schemas.trip import TripCreate, TripResponse
from app.schemas.user import (
    STUDENT_EMAIL_DOMAIN,
    UserBase,
    UserCreate,
    UserResponse,
    validate_student_domain,
)

__all__ = [
    "STUDENT_EMAIL_DOMAIN",
    "UserBase",
    "UserCreate",
    "UserResponse",
    "validate_student_domain",
    "BusBase",
    "BusCreate",
    "BusUpdate",
    "BusResponse",
    "RouteBase",
    "RouteCreate",
    "RouteUpdate",
    "RouteResponse",
    "BoardingPointBase",
    "BoardingPointCreate",
    "BoardingPointUpdate",
    "BoardingPointResponse",
    "RouteStopBase",
    "RouteStopCreate",
    "RouteStopUpdate",
    "RouteStopOrderUpdate",
    "RouteStopResponse",
    "DriverAssignmentResponse",
    "TripCreate",
    "TripResponse",
    "LocationPingCreate",
    "LocationPingResponse",
    "LiveLocationResponse",
    "GPSPointSyncItem",
    "GPSBatchSyncRequest",
    "GPSBatchSyncResponse",
    "ParentRegisterRequest",
    "ParentLinkRequestResponse",
    "ParentChildResponse",
    "StopETAResponse",
    "TripETAResponse",
]


