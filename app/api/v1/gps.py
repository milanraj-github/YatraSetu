import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_role, require_roles
from app.db.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.gps import LocationPingCreate, LocationPingResponse
from app.services import gps_service

router = APIRouter(prefix="/trips", tags=["GPS Telemetry"])


@router.post(
    "/{trip_id}/gps",
    response_model=LocationPingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Driver GPS Location Ping",
    description="Ingest a live GPS telemetry reading for an IN_PROGRESS trip (Assigned DRIVER only).",
)
async def ingest_trip_gps_endpoint(
    trip_id: uuid.UUID,
    ping_in: LocationPingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DRIVER)),
) -> LocationPingResponse:
    """Ingest a GPS location ping from the assigned driver."""
    return await gps_service.ingest_location_ping(db, trip_id, current_user, ping_in)


@router.get(
    "/{trip_id}/gps",
    response_model=List[LocationPingResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Historical GPS Location Pings for a Trip",
    description="Retrieve chronological GPS history for a trip (ADMIN or assigned DRIVER).",
)
async def get_trip_gps_history_endpoint(
    trip_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DRIVER)),
) -> List[LocationPingResponse]:
    """Retrieve chronological GPS history for a trip."""
    return await gps_service.get_trip_location_history(db, trip_id, current_user)
