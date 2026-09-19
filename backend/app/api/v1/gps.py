import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_role, require_roles
from app.db.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.gps import (
    GPSBatchSyncRequest,
    GPSBatchSyncResponse,
    LiveLocationResponse,
    LocationPingCreate,
    LocationPingResponse,
)
from app.services import gps_service

router = APIRouter(prefix="/trips", tags=["GPS Telemetry & Live Location"])


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


@router.post(
    "/{trip_id}/gps/sync",
    response_model=GPSBatchSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Sync Offline GPS Batch for a Trip",
    description="Ingest a batch of offline-queued GPS telemetry readings for an IN_PROGRESS trip (Assigned DRIVER only) with deduplication.",
)
async def sync_trip_gps_batch_endpoint(
    trip_id: uuid.UUID,
    batch_in: GPSBatchSyncRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DRIVER)),
) -> GPSBatchSyncResponse:
    """Ingest a batch of offline-queued GPS points from the assigned driver."""
    return await gps_service.sync_location_pings_batch(db, trip_id, current_user, batch_in)



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


@router.get(
    "/{trip_id}/live",
    response_model=LiveLocationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current Live Location for a Trip",
    description="Retrieve the latest cached live location for an active trip from Redis (ADMIN or assigned DRIVER).",
)
async def get_trip_live_location_endpoint(
    trip_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DRIVER)),
) -> LiveLocationResponse:
    """Retrieve the latest cached live location for a trip."""
    return await gps_service.get_trip_live_location(db, trip_id, current_user)
