from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_driver
from app.schemas.auth import UserResponse, APIResponse
from app.schemas.tracking import (
    GpsIngestRequest, DriverTrackingStatusResponse, LiveTripResponse, ActiveBusTrackingItem
)
from app.services.tracking_service import (
    get_driver_tracking_status, ingest_gps_ping, get_live_trip_location, get_all_active_buses, GPSValidationError
)
from app.models.user import User

router = APIRouter(tags=["Tracking & Location"])

async def get_db_user_from_auth(db: AsyncSession, auth_user: UserResponse) -> User:
    """
    Resolves the full DB User record from the authenticated Firebase identity.
    Raises HTTP 404 if the user has not been synced to the database yet.
    Clients must call POST /auth/sync-user on first login.
    """
    from sqlalchemy.future import select
    from fastapi import HTTPException, status as http_status

    stmt = select(User).where(User.firebase_uid == auth_user.firebase_uid)
    res = await db.execute(stmt)
    user = res.scalars().first()

    if not user:
        # Fallback: try matching by email (handles legacy seeded accounts)
        stmt_email = select(User).where(User.email == auth_user.email)
        res_email = await db.execute(stmt_email)
        user = res_email.scalars().first()

    if not user:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail={
                "code": "USER_NOT_FOUND_IN_DB",
                "message": "User not found in database. Please call POST /api/v1/auth/sync-user first.",
            }
        )

    return user

@router.get("/driver/tracking/status", response_model=APIResponse[DriverTrackingStatusResponse])
async def get_driver_status(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(require_driver)
):
    """
    Returns active bus assignment, route, schedule, and tracking status for authenticated driver.
    """
    driver_user = await get_db_user_from_auth(db, current_user)
    status_data = await get_driver_tracking_status(db, driver_user)
    return APIResponse(success=True, data=status_data)

@router.post("/gps/ingest", response_model=APIResponse[Dict[str, Any]])
async def ingest_gps(
    ping_data: GpsIngestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(require_driver)
):
    """
    Ingests live GPS ping from driver app. Validates session, protects against duplicates,
    stores in PostgreSQL location history and updates Redis latest location cache if newer.
    """
    driver_user = await get_db_user_from_auth(db, current_user)
    try:
        res = await ingest_gps_ping(db, driver_user, ping_data)
        return APIResponse(success=True, data=res)
    except GPSValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message}
        )

@router.get("/trips/{trip_id}/live", response_model=APIResponse[LiveTripResponse])
async def get_trip_live(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Returns live tracking status and current location for a specific trip session.
    """
    try:
        res = await get_live_trip_location(db, trip_id)
        return APIResponse(success=True, data=res)
    except GPSValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": e.code, "message": e.message}
        )

@router.get("/tracking/active-buses", response_model=APIResponse[List[ActiveBusTrackingItem]])
async def get_active_buses(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Returns list of all currently active buses with latest locations, driver names, and trip info.
    """
    res = await get_all_active_buses(db)
    return APIResponse(success=True, data=res)
