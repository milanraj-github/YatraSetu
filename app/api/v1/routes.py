import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_role
from app.db.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.route import RouteCreate, RouteResponse, RouteUpdate
from app.schemas.route_stop import (
    RouteStopCreate,
    RouteStopOrderUpdate,
    RouteStopResponse,
    RouteStopUpdate,
)
from app.services import route_service, route_stop_service

router = APIRouter(prefix="/routes", tags=["Route Management"])


# ==========================================
# 1. ROUTE CRUD
# ==========================================

@router.post(
    "",
    response_model=RouteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Route",
    description="Register a new bus route (ADMIN only).",
)
async def create_route_endpoint(
    route_in: RouteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> RouteResponse:
    """Create a new route."""
    route = await route_service.create_route(db, route_in)
    return RouteResponse.model_validate(route)


@router.get(
    "",
    response_model=List[RouteResponse],
    status_code=status.HTTP_200_OK,
    summary="List Routes",
    description="Retrieve a paginated list of routes (ADMIN only).",
)
async def list_routes_endpoint(
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Max records to return"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> List[RouteResponse]:
    """List all routes."""
    routes = await route_service.list_routes(db, skip=skip, limit=limit, is_active=is_active)
    return [RouteResponse.model_validate(r) for r in routes]


@router.get(
    "/{route_id}",
    response_model=RouteResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Route by ID",
    description="Retrieve details of a specific route (ADMIN only).",
)
async def get_route_endpoint(
    route_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> RouteResponse:
    """Get single route details."""
    route = await route_service.get_route_by_id(db, route_id)
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found",
        )
    return RouteResponse.model_validate(route)


@router.patch(
    "/{route_id}",
    response_model=RouteResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Route",
    description="Update route details (ADMIN only).",
)
async def update_route_endpoint(
    route_id: uuid.UUID,
    route_in: RouteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> RouteResponse:
    """Update route attributes."""
    route = await route_service.get_route_by_id(db, route_id)
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found",
        )
    updated_route = await route_service.update_route(db, route, route_in)
    return RouteResponse.model_validate(updated_route)


@router.delete(
    "/{route_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate Route",
    description="Safely deactivate a route (sets is_active = false) (ADMIN only).",
)
async def deactivate_route_endpoint(
    route_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> Response:
    """Deactivate a route."""
    route = await route_service.get_route_by_id(db, route_id)
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found",
        )
    await route_service.deactivate_route(db, route)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ==========================================
# 2. ROUTE STOPS MANAGEMENT
# ==========================================

@router.post(
    "/{route_id}/stops",
    response_model=RouteStopResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Stop to Route",
    description="Add a boarding point to the route stop sequence (ADMIN only).",
)
async def add_stop_endpoint(
    route_id: uuid.UUID,
    stop_in: RouteStopCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> RouteStopResponse:
    """Add a stop to a route."""
    route_stop = await route_stop_service.add_stop_to_route(db, route_id, stop_in)
    return RouteStopResponse.model_validate(route_stop)


@router.get(
    "/{route_id}/stops",
    response_model=List[RouteStopResponse],
    status_code=status.HTTP_200_OK,
    summary="List Stops for Route",
    description="Retrieve the ordered list of stops for a route (ADMIN only).",
)
async def list_stops_endpoint(
    route_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> List[RouteStopResponse]:
    """List ordered stops for a route."""
    stops = await route_stop_service.list_stops_for_route(db, route_id)
    return [RouteStopResponse.model_validate(s) for s in stops]


@router.patch(
    "/{route_id}/stops/{route_stop_id}",
    response_model=RouteStopResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Route Stop",
    description="Update stop arrival offset time (ADMIN only).",
)
async def update_stop_endpoint(
    route_id: uuid.UUID,
    route_stop_id: uuid.UUID,
    stop_in: RouteStopUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> RouteStopResponse:
    """Update route stop."""
    route_stop = await route_stop_service.get_route_stop_by_id(db, route_stop_id)
    if not route_stop or route_stop.route_id != route_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route stop not found on this route",
        )
    updated_stop = await route_stop_service.update_route_stop(db, route_stop, stop_in)
    return RouteStopResponse.model_validate(updated_stop)


@router.delete(
    "/{route_id}/stops/{route_stop_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove Stop from Route",
    description="Remove a stop from the route and recompact stop sequence (ADMIN only).",
)
async def remove_stop_endpoint(
    route_id: uuid.UUID,
    route_stop_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> Response:
    """Remove stop from route."""
    route_stop = await route_stop_service.get_route_stop_by_id(db, route_stop_id)
    if not route_stop or route_stop.route_id != route_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route stop not found on this route",
        )
    await route_stop_service.remove_stop_from_route(db, route_stop)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch(
    "/{route_id}/stops/{route_stop_id}/order",
    response_model=List[RouteStopResponse],
    status_code=status.HTTP_200_OK,
    summary="Reorder Route Stop",
    description="Safely change the sequence position of a stop on a route (ADMIN only).",
)
async def reorder_stop_endpoint(
    route_id: uuid.UUID,
    route_stop_id: uuid.UUID,
    order_in: RouteStopOrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> List[RouteStopResponse]:
    """Reorder route stops."""
    reordered_stops = await route_stop_service.reorder_route_stops(
        db, route_id, route_stop_id, order_in.new_stop_order
    )
    return [RouteStopResponse.model_validate(s) for s in reordered_stops]
