import uuid
from datetime import datetime, timezone
from typing import Sequence
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TripStatus, UserRole
from app.models.location import LocationPing
from app.models.trip import Trip
from app.models.user import User
from app.schemas.gps import LocationPingCreate


async def ingest_location_ping(
    db: AsyncSession,
    trip_id: uuid.UUID,
    current_user: User,
    ping_in: LocationPingCreate,
) -> LocationPing:
    """Ingest and persist a GPS telemetry ping for an active trip."""
    # 1. Enforce DRIVER role strictly (Admin cannot ingest GPS on behalf of driver)
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only authenticated drivers can submit GPS location pings",
        )

    # 2. Retrieve trip
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )

    # 3. Enforce Driver Ownership and Assigned Bus verification
    if trip.driver_id != current_user.id or trip.bus_id != current_user.assigned_bus_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: driver is not assigned to operate this trip and bus",
        )

    # 4. Verify Trip Status (Only IN_PROGRESS trips accept GPS)
    if trip.status != TripStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot ingest GPS for trip with status '{trip.status.value}'. Trip must be IN_PROGRESS.",
        )

    # 5. Generate server-controlled received_at timestamp
    server_received_at = datetime.now(timezone.utc)

    location_ping = LocationPing(
        trip_id=trip.id,
        driver_id=current_user.id,
        latitude=ping_in.latitude,
        longitude=ping_in.longitude,
        recorded_at=ping_in.recorded_at,
        received_at=server_received_at,
        accuracy_meters=ping_in.accuracy_meters,
        speed_mps=ping_in.speed_mps,
        heading_degrees=ping_in.heading_degrees,
    )

    db.add(location_ping)
    await db.commit()
    await db.refresh(location_ping)

    return location_ping


async def get_trip_location_history(
    db: AsyncSession,
    trip_id: uuid.UUID,
    current_user: User,
) -> Sequence[LocationPing]:
    """Retrieve historical GPS location points for a trip ordered chronologically."""
    # 1. Retrieve trip
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )

    # 2. Enforce role permissions (ADMIN sees all, DRIVER only sees their own trip)
    if current_user.role == UserRole.DRIVER and trip.driver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Drivers can only view GPS history for their own trips",
        )

    # 3. Retrieve location pings ordered chronologically
    pings_result = await db.execute(
        select(LocationPing)
        .where(LocationPing.trip_id == trip_id)
        .order_by(
            LocationPing.recorded_at.asc(),
            LocationPing.received_at.asc(),
            LocationPing.id.asc(),
        )
    )
    return pings_result.scalars().all()
