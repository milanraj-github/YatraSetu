import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.bus import Bus
from app.models.enums import TripStatus, UserRole
from app.models.route import Route
from app.models.trip import Trip
from app.models.user import User
from app.schemas.trip import TripCreate


def verify_driver_trip_access(current_user: User, trip: Trip) -> None:
    """Enforce driver ownership and assigned bus matching rule."""
    if current_user.role == UserRole.ADMIN:
        return

    if current_user.role == UserRole.DRIVER:
        if trip.driver_id != current_user.id or trip.bus_id != current_user.assigned_bus_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: driver ownership mismatch or unassigned bus",
            )
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access forbidden: only administrators and assigned drivers can manage trip lifecycle",
    )


async def create_trip(db: AsyncSession, trip_in: TripCreate) -> Trip:
    """Schedule a new trip after validating active route, active bus, and driver bus assignment."""
    # 1. Verify route exists and is active
    res_route = await db.execute(select(Route).where(Route.id == trip_in.route_id))
    route = res_route.scalar_one_or_none()
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found",
        )
    if not route.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot schedule a trip with an inactive route",
        )

    # 2. Verify bus exists and is active
    res_bus = await db.execute(select(Bus).where(Bus.id == trip_in.bus_id))
    bus = res_bus.scalar_one_or_none()
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found",
        )
    if not bus.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot schedule a trip with an inactive bus",
        )

    # 3. Verify driver exists and is a DRIVER
    res_driver = await db.execute(select(User).where(User.id == trip_in.driver_id))
    driver = res_driver.scalar_one_or_none()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver user not found",
        )
    if driver.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User is not a driver (role is {driver.role.value})",
        )

    # 4. Verify driver is assigned to the specified bus
    if driver.assigned_bus_id != trip_in.bus_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Driver is not assigned to the selected bus",
        )

    trip = Trip(
        route_id=trip_in.route_id,
        bus_id=trip_in.bus_id,
        driver_id=trip_in.driver_id,
        status=TripStatus.SCHEDULED,
        scheduled_start_at=trip_in.scheduled_start_at,
    )
    db.add(trip)
    await db.commit()
    await db.refresh(trip)
    return trip


async def get_trip_by_id(db: AsyncSession, trip_id: uuid.UUID) -> Optional[Trip]:
    """Retrieve a single trip by ID."""
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    return result.scalar_one_or_none()


async def list_trips(
    db: AsyncSession,
    current_user: User,
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[TripStatus] = None,
    route_id: Optional[uuid.UUID] = None,
    bus_id: Optional[uuid.UUID] = None,
) -> List[Trip]:
    """List trips with role-based visibility (ADMIN sees all, DRIVER sees own)."""
    query = select(Trip).order_by(Trip.created_at.desc()).offset(skip).limit(limit)

    if current_user.role == UserRole.DRIVER:
        query = query.where(Trip.driver_id == current_user.id)

    if status_filter is not None:
        query = query.where(Trip.status == status_filter)
    if route_id is not None:
        query = query.where(Trip.route_id == route_id)
    if bus_id is not None:
        query = query.where(Trip.bus_id == bus_id)

    result = await db.execute(query)
    return list(result.scalars().all())


async def start_trip(db: AsyncSession, trip: Trip, current_user: User) -> Trip:
    """Transition a SCHEDULED trip to IN_PROGRESS (ADMIN or assigned DRIVER)."""
    verify_driver_trip_access(current_user, trip)

    if trip.status != TripStatus.SCHEDULED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot start trip in '{trip.status.value}' status. Only SCHEDULED trips can be started.",
        )

    trip.status = TripStatus.IN_PROGRESS
    trip.actual_start_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(trip)
    return trip


async def end_trip(db: AsyncSession, trip: Trip, current_user: User) -> Trip:
    """Transition an IN_PROGRESS trip to COMPLETED (ADMIN or assigned DRIVER)."""
    from app.services.gps_service import cleanup_trip_live_location

    verify_driver_trip_access(current_user, trip)

    if trip.status != TripStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot end trip in '{trip.status.value}' status. Only IN_PROGRESS trips can be ended.",
        )

    trip.status = TripStatus.COMPLETED
    trip.actual_end_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(trip)

    # Cleanup live location cache from Redis
    await cleanup_trip_live_location(trip.id)

    return trip


async def cancel_trip(db: AsyncSession, trip: Trip, current_user: User) -> Trip:
    """Transition a SCHEDULED trip to CANCELLED (ADMIN only)."""
    from app.services.gps_service import cleanup_trip_live_location

    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can cancel trips",
        )

    if trip.status != TripStatus.SCHEDULED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel trip in '{trip.status.value}' status. Only SCHEDULED trips can be cancelled.",
        )

    trip.status = TripStatus.CANCELLED
    await db.commit()
    await db.refresh(trip)

    # Cleanup live location cache from Redis if any exists
    await cleanup_trip_live_location(trip.id)

    return trip
