import uuid
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.boarding_point import BoardingPoint
from app.models.route import Route
from app.models.route_stop import RouteStop
from app.schemas.route_stop import RouteStopCreate, RouteStopUpdate


async def add_stop_to_route(
    db: AsyncSession, route_id: uuid.UUID, stop_in: RouteStopCreate
) -> RouteStop:
    """Add a boarding point as an ordered stop on a route."""
    # 1. Verify route exists and is active
    res_route = await db.execute(select(Route).where(Route.id == route_id))
    route = res_route.scalar_one_or_none()
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found",
        )
    if not route.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add stops to an inactive route",
        )

    # 2. Verify boarding point exists and is active
    res_bp = await db.execute(
        select(BoardingPoint).where(BoardingPoint.id == stop_in.boarding_point_id)
    )
    bp = res_bp.scalar_one_or_none()
    if not bp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Boarding point not found",
        )
    if not bp.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add an inactive boarding point to a route",
        )

    # 3. Verify stop_order uniqueness within this route
    res_order = await db.execute(
        select(RouteStop).where(
            RouteStop.route_id == route_id,
            RouteStop.stop_order == stop_in.stop_order,
        )
    )
    if res_order.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stop order {stop_in.stop_order} is already taken on this route",
        )

    # 4. Verify boarding_point uniqueness within this route
    res_dup_bp = await db.execute(
        select(RouteStop).where(
            RouteStop.route_id == route_id,
            RouteStop.boarding_point_id == stop_in.boarding_point_id,
        )
    )
    if res_dup_bp.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Boarding point is already configured on this route",
        )

    route_stop = RouteStop(
        route_id=route_id,
        boarding_point_id=stop_in.boarding_point_id,
        stop_order=stop_in.stop_order,
        scheduled_arrival_offset_minutes=stop_in.scheduled_arrival_offset_minutes or 0,
    )
    db.add(route_stop)
    await db.commit()
    await db.refresh(route_stop, attribute_names=["boarding_point"])
    return route_stop


async def list_stops_for_route(
    db: AsyncSession, route_id: uuid.UUID
) -> List[RouteStop]:
    """Retrieve all stops for a route ordered by stop sequence."""
    res_route = await db.execute(select(Route).where(Route.id == route_id))
    if res_route.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found",
        )

    query = (
        select(RouteStop)
        .where(RouteStop.route_id == route_id)
        .order_by(RouteStop.stop_order.asc())
        .options(selectinload(RouteStop.boarding_point))
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_route_stop_by_id(
    db: AsyncSession, route_stop_id: uuid.UUID
) -> Optional[RouteStop]:
    """Retrieve a single route stop by its UUID."""
    result = await db.execute(
        select(RouteStop)
        .where(RouteStop.id == route_stop_id)
        .options(selectinload(RouteStop.boarding_point))
    )
    return result.scalar_one_or_none()


async def update_route_stop(
    db: AsyncSession, route_stop: RouteStop, stop_in: RouteStopUpdate
) -> RouteStop:
    """Update route stop properties such as arrival offset."""
    if stop_in.scheduled_arrival_offset_minutes is not None:
        route_stop.scheduled_arrival_offset_minutes = (
            stop_in.scheduled_arrival_offset_minutes
        )

    await db.commit()
    await db.refresh(route_stop, attribute_names=["boarding_point"])
    return route_stop


async def remove_stop_from_route(db: AsyncSession, route_stop: RouteStop) -> None:
    """Remove a stop from a route and recompact remaining stop sequence."""
    route_id = route_stop.route_id
    await db.delete(route_stop)
    await db.flush()

    # Recompact remaining stops to maintain sequential 1..N order
    remaining_stops = await list_stops_for_route(db, route_id)
    for index, stop in enumerate(remaining_stops, start=1):
        stop.stop_order = index

    await db.commit()


async def reorder_route_stops(
    db: AsyncSession,
    route_id: uuid.UUID,
    target_stop_id: uuid.UUID,
    new_order: int,
) -> List[RouteStop]:
    """Safely reorder stops within a route without violating unique constraints."""
    stops = await list_stops_for_route(db, route_id)
    if not stops:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No stops found for this route",
        )

    target_stop = next((s for s in stops if s.id == target_stop_id), None)
    if not target_stop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route stop not found on this route",
        )

    total_stops = len(stops)
    if new_order < 1 or new_order > total_stops:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"new_stop_order must be between 1 and {total_stops}",
        )

    # Re-order the in-memory sequence
    stops.remove(target_stop)
    stops.insert(new_order - 1, target_stop)

    # Phase 1: Assign temporary offset values to prevent collision
    for i, s in enumerate(stops, start=1):
        s.stop_order = 10000 + i
    await db.flush()

    # Phase 2: Assign final sequential numbers 1..N
    for i, s in enumerate(stops, start=1):
        s.stop_order = i
    await db.flush()

    await db.commit()

    # Return refreshed stops
    return await list_stops_for_route(db, route_id)
