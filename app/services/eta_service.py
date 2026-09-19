import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.redis import get_redis_client
from app.models.enums import TripStatus, UserRole
from app.models.parent_child import ParentChildren
from app.models.route_stop import RouteStop
from app.models.trip import Trip
from app.models.user import User
from app.schemas.eta import StopETAResponse, TripETAResponse
from app.services import geofence_service
from app.services.gps_service import get_live_location_key

logger = logging.getLogger(__name__)


async def get_trip_eta(
    db: AsyncSession,
    trip_id: uuid.UUID,
    current_user: User,
) -> TripETAResponse:
    """Calculate baseline deterministic arrival time estimates for an active trip's route stops."""
    # 1. Retrieve trip from database
    trip_result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = trip_result.scalar_one_or_none()
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )

    # 2. Enforce role-based access control and ownership
    if current_user.role == UserRole.ADMIN:
        # Admin can view ETA for any valid trip
        pass
    elif current_user.role == UserRole.DRIVER:
        # Driver can view ETA only for their own assigned trip
        if trip.driver_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Drivers can only view ETA for their own assigned trips",
            )
    elif current_user.role == UserRole.PARENT:
        # Parent can view ETA only if they have an approved relationship with a student assigned to this trip's bus
        parent_link_query = (
            select(ParentChildren)
            .join(User, ParentChildren.student_id == User.id)
            .where(
                ParentChildren.parent_id == current_user.id,
                User.assigned_bus_id == trip.bus_id,
            )
        )
        link_result = await db.execute(parent_link_query)
        if not link_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You do not have an approved child assigned to this trip's bus",
            )
    elif current_user.role == UserRole.STUDENT:
        # Student can view ETA only if assigned to this trip's bus
        if current_user.assigned_bus_id != trip.bus_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You are not assigned to this trip's bus",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Unauthorized role for ETA retrieval",
        )

    # 3. Verify Trip Lifecycle Status (ETA is only valid for IN_PROGRESS trips)
    if trip.status != TripStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot calculate ETA for trip with status '{trip.status.value}'. Trip must be IN_PROGRESS.",
        )

    # 4. Fetch current live location state from Redis
    try:
        redis_client = get_redis_client()
        key = get_live_location_key(trip.id)
        raw_data = await redis_client.get(key)
    except Exception as exc:
        logger.error(f"Redis error retrieving live location for trip {trip.id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Live location service temporarily unavailable",
        )

    if not raw_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No live location available for this trip",
        )

    live_data = json.loads(raw_data)
    current_lat = float(live_data["latitude"])
    current_lon = float(live_data["longitude"])

    # 5. Fetch ordered RouteStops with BoardingPoints for the trip's route
    stops_stmt = (
        select(RouteStop)
        .options(selectinload(RouteStop.boarding_point))
        .where(RouteStop.route_id == trip.route_id)
        .order_by(RouteStop.stop_order.asc())
    )
    stops_result = await db.execute(stops_stmt)
    route_stops: List[RouteStop] = list(stops_result.scalars().all())

    # 6. Validate configured baseline speed
    speed_mps = settings.DEFAULT_ETA_SPEED_MPS
    if speed_mps <= 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid ETA speed configuration: DEFAULT_ETA_SPEED_MPS must be greater than 0",
        )

    # 7. Calculate PostGIS distance and deterministic ETA for each route stop
    now_utc = datetime.now(timezone.utc)
    stops_eta: List[StopETAResponse] = []

    for route_stop in route_stops:
        bp = route_stop.boarding_point
        if not bp:
            continue

        distance_meters = await geofence_service.calculate_distance_meters(
            lat1=current_lat,
            lon1=current_lon,
            lat2=bp.latitude,
            lon2=bp.longitude,
            db=db,
        )

        eta_seconds = max(0.0, distance_meters / speed_mps)
        estimated_arrival = now_utc + timedelta(seconds=eta_seconds)

        stops_eta.append(
            StopETAResponse(
                stop_id=route_stop.id,
                stop_order=route_stop.stop_order,
                boarding_point_id=bp.id,
                boarding_point_name=bp.name,
                latitude=bp.latitude,
                longitude=bp.longitude,
                distance_meters=round(distance_meters, 2),
                eta_seconds=round(eta_seconds, 1),
                estimated_arrival_at=estimated_arrival,
            )
        )

    return TripETAResponse(
        trip_id=trip.id,
        generated_at=now_utc,
        current_latitude=current_lat,
        current_longitude=current_lon,
        stops=stops_eta,
    )
