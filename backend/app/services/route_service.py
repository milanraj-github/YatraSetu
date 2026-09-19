import uuid
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.route import Route
from app.models.route_stop import RouteStop
from app.schemas.route import RouteCreate, RouteUpdate


async def create_route(db: AsyncSession, route_in: RouteCreate) -> Route:
    """Create a new route after verifying code uniqueness."""
    res = await db.execute(select(Route).where(Route.code == route_in.code))
    if res.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Route with code '{route_in.code}' already exists",
        )

    route = Route(
        name=route_in.name,
        code=route_in.code,
        description=route_in.description,
        is_active=route_in.is_active,
    )
    db.add(route)
    await db.commit()
    await db.refresh(route)
    return route


async def get_route_by_id(
    db: AsyncSession, route_id: uuid.UUID, include_stops: bool = False
) -> Optional[Route]:
    """Retrieve route by ID."""
    query = select(Route).where(Route.id == route_id)
    if include_stops:
        query = query.options(
            selectinload(Route.route_stops).selectinload(RouteStop.boarding_point)
        )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def list_routes(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
) -> List[Route]:
    """List routes with pagination."""
    query = select(Route).order_by(Route.created_at.desc()).offset(skip).limit(limit)
    if is_active is not None:
        query = query.where(Route.is_active == is_active)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_route(db: AsyncSession, route: Route, route_in: RouteUpdate) -> Route:
    """Update route attributes with code uniqueness verification."""
    update_data = route_in.model_dump(exclude_unset=True)

    if "code" in update_data and update_data["code"] != route.code:
        res = await db.execute(
            select(Route).where(Route.code == update_data["code"], Route.id != route.id)
        )
        if res.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Route with code '{update_data['code']}' already exists",
            )
        route.code = update_data["code"]

    if "name" in update_data and update_data["name"] is not None:
        route.name = update_data["name"]

    if "description" in update_data:
        route.description = update_data["description"]

    if "is_active" in update_data and update_data["is_active"] is not None:
        route.is_active = update_data["is_active"]

    await db.commit()
    await db.refresh(route)
    return route


async def deactivate_route(db: AsyncSession, route: Route) -> Route:
    """Safely deactivate a route."""
    route.is_active = False
    await db.commit()
    await db.refresh(route)
    return route
