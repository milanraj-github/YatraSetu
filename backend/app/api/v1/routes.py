"""
Admin: Route & boarding-point management endpoints.

Boarding Points (stops):
  GET    /api/v1/stops                     — List all stops
  POST   /api/v1/stops                     — Create a stop (Admin)
  GET    /api/v1/stops/{stop_id}           — Get a single stop
  PATCH  /api/v1/stops/{stop_id}           — Update a stop (Admin)
  DELETE /api/v1/stops/{stop_id}           — Delete a stop (Admin)

Routes:
  GET    /api/v1/routes                    — List all routes (with stops)
  POST   /api/v1/routes                    — Create route + stops (Admin)
  GET    /api/v1/routes/{route_id}         — Get a single route with stops
  PATCH  /api/v1/routes/{route_id}         — Update route name (Admin)
  DELETE /api/v1/routes/{route_id}         — Delete route (Admin)
  POST   /api/v1/routes/{route_id}/stops   — Add a stop to route (Admin)
  DELETE /api/v1/routes/{route_id}/stops/{stop_id} — Remove stop from route (Admin)
"""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.schemas.auth import APIResponse
from app.schemas.management import (
    BoardingPointCreate, BoardingPointUpdate, BoardingPointResponse,
    RouteCreate, RouteUpdate, RouteStopInput, RouteStopResponse, RouteResponse,
)
from app.models.route import BoardingPoint, Route, RouteStop, RouteDirection

logger = logging.getLogger("smartbus.routes")

stops_router = APIRouter(prefix="/stops", tags=["Boarding Points / Stops"])
routes_router = APIRouter(prefix="/routes", tags=["Routes"])


# ─────────────────────────────────────────────────────────────────────────────
# STOPS (Boarding Points)
# ─────────────────────────────────────────────────────────────────────────────

@stops_router.get("", response_model=APIResponse[List[BoardingPointResponse]])
async def list_stops(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(BoardingPoint).order_by(BoardingPoint.name))
    return APIResponse(success=True, data=[BoardingPointResponse.model_validate(s) for s in result.scalars().all()])


@stops_router.post("", response_model=APIResponse[BoardingPointResponse], status_code=status.HTTP_201_CREATED)
async def create_stop(payload: BoardingPointCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """Create a boarding point / stop. Admin only."""
    existing = await db.execute(select(BoardingPoint).where(BoardingPoint.name == payload.name))
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "STOP_ALREADY_EXISTS", "message": f"A stop named '{payload.name}' already exists."},
        )
    stop = BoardingPoint(**payload.model_dump())
    db.add(stop)
    await db.commit()
    await db.refresh(stop)
    logger.info(f"Stop created: {stop.name} (id={stop.id})")
    return APIResponse(success=True, data=BoardingPointResponse.model_validate(stop))


@stops_router.get("/{stop_id}", response_model=APIResponse[BoardingPointResponse])
async def get_stop(stop_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(BoardingPoint).where(BoardingPoint.id == stop_id))
    stop = result.scalars().first()
    if not stop:
        raise HTTPException(status_code=404, detail={"code": "STOP_NOT_FOUND", "message": f"Stop id={stop_id} not found."})
    return APIResponse(success=True, data=BoardingPointResponse.model_validate(stop))


@stops_router.patch("/{stop_id}", response_model=APIResponse[BoardingPointResponse])
async def update_stop(stop_id: int, payload: BoardingPointUpdate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(BoardingPoint).where(BoardingPoint.id == stop_id))
    stop = result.scalars().first()
    if not stop:
        raise HTTPException(status_code=404, detail={"code": "STOP_NOT_FOUND", "message": f"Stop id={stop_id} not found."})
    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(stop, field, val)
    await db.commit()
    await db.refresh(stop)
    return APIResponse(success=True, data=BoardingPointResponse.model_validate(stop))


@stops_router.delete("/{stop_id}", response_model=APIResponse[dict])
async def delete_stop(stop_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(BoardingPoint).where(BoardingPoint.id == stop_id))
    stop = result.scalars().first()
    if not stop:
        raise HTTPException(status_code=404, detail={"code": "STOP_NOT_FOUND", "message": f"Stop id={stop_id} not found."})
    await db.delete(stop)
    await db.commit()
    return APIResponse(success=True, data={"message": f"Stop '{stop.name}' deleted."})


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

async def _load_route(db: AsyncSession, route_id: int) -> Route:
    result = await db.execute(
        select(Route).options(
            selectinload(Route.stops).selectinload(RouteStop.boarding_point)
        ).where(Route.id == route_id)
    )
    route = result.scalars().first()
    if not route:
        raise HTTPException(status_code=404, detail={"code": "ROUTE_NOT_FOUND", "message": f"Route id={route_id} not found."})
    return route


@routes_router.get("", response_model=APIResponse[List[RouteResponse]])
async def list_routes(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(
        select(Route).options(selectinload(Route.stops).selectinload(RouteStop.boarding_point)).order_by(Route.id)
    )
    return APIResponse(success=True, data=[RouteResponse.model_validate(r) for r in result.scalars().all()])


@routes_router.post("", response_model=APIResponse[RouteResponse], status_code=status.HTTP_201_CREATED)
async def create_route(payload: RouteCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """Create a route and optionally set its stops in one call. Admin only."""
    existing = await db.execute(select(Route).where(Route.code == payload.code))
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "ROUTE_CODE_EXISTS", "message": f"Route code '{payload.code}' already in use."},
        )

    route = Route(name=payload.name, code=payload.code)
    db.add(route)
    await db.flush()  # get route.id before inserting stops

    for stop_in in (payload.stops or []):
        # Verify boarding_point exists
        bp = await db.execute(select(BoardingPoint).where(BoardingPoint.id == stop_in.boarding_point_id))
        if not bp.scalars().first():
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "BOARDING_POINT_NOT_FOUND", "message": f"Boarding point id={stop_in.boarding_point_id} not found."},
            )
        rs = RouteStop(
            route_id=route.id,
            boarding_point_id=stop_in.boarding_point_id,
            sequence_order=stop_in.sequence_order,
            direction=RouteDirection(stop_in.direction.value),
        )
        db.add(rs)

    await db.commit()
    route = await _load_route(db, route.id)
    logger.info(f"Route created: {route.code} (id={route.id})")
    return APIResponse(success=True, data=RouteResponse.model_validate(route))


@routes_router.get("/{route_id}", response_model=APIResponse[RouteResponse])
async def get_route(route_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    route = await _load_route(db, route_id)
    return APIResponse(success=True, data=RouteResponse.model_validate(route))


@routes_router.patch("/{route_id}", response_model=APIResponse[RouteResponse])
async def update_route(route_id: int, payload: RouteUpdate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    route = await _load_route(db, route_id)
    if payload.name is not None:
        route.name = payload.name
    await db.commit()
    route = await _load_route(db, route_id)
    return APIResponse(success=True, data=RouteResponse.model_validate(route))


@routes_router.delete("/{route_id}", response_model=APIResponse[dict])
async def delete_route(route_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    route = await _load_route(db, route_id)
    await db.delete(route)
    await db.commit()
    return APIResponse(success=True, data={"message": f"Route '{route.name}' deleted."})


@routes_router.post("/{route_id}/stops", response_model=APIResponse[RouteResponse], status_code=status.HTTP_201_CREATED)
async def add_stop_to_route(route_id: int, stop_in: RouteStopInput, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """Add a boarding point to an existing route. Admin only."""
    route = await _load_route(db, route_id)
    bp = await db.execute(select(BoardingPoint).where(BoardingPoint.id == stop_in.boarding_point_id))
    if not bp.scalars().first():
        raise HTTPException(
            status_code=422,
            detail={"code": "BOARDING_POINT_NOT_FOUND", "message": f"Boarding point id={stop_in.boarding_point_id} not found."},
        )
    rs = RouteStop(
        route_id=route_id,
        boarding_point_id=stop_in.boarding_point_id,
        sequence_order=stop_in.sequence_order,
        direction=RouteDirection(stop_in.direction.value),
    )
    db.add(rs)
    await db.commit()
    route = await _load_route(db, route_id)
    return APIResponse(success=True, data=RouteResponse.model_validate(route))


@routes_router.delete("/{route_id}/stops/{route_stop_id}", response_model=APIResponse[dict])
async def remove_stop_from_route(route_id: int, route_stop_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """Remove a route stop (by RouteStop.id). Admin only."""
    result = await db.execute(select(RouteStop).where(RouteStop.id == route_stop_id, RouteStop.route_id == route_id))
    rs = result.scalars().first()
    if not rs:
        raise HTTPException(status_code=404, detail={"code": "ROUTE_STOP_NOT_FOUND", "message": f"RouteStop id={route_stop_id} not found on route {route_id}."})
    await db.delete(rs)
    await db.commit()
    return APIResponse(success=True, data={"message": "Stop removed from route."})

from pydantic import BaseModel
class RouteStopReorderInput(BaseModel):
    route_stop_id: int
    new_sequence_order: int

@routes_router.put("/{route_id}/stops/reorder", response_model=APIResponse[RouteResponse])
async def reorder_route_stops(route_id: int, payload: List[RouteStopReorderInput], db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """Reorder stops for a route."""
    route = await _load_route(db, route_id)
    
    # Fetch all stops to update
    stops_to_update = []
    for item in payload:
        rs = await db.execute(select(RouteStop).where(RouteStop.id == item.route_stop_id, RouteStop.route_id == route_id))
        stop = rs.scalars().first()
        if not stop:
            raise HTTPException(status_code=404, detail={"code": "ROUTE_STOP_NOT_FOUND", "message": f"RouteStop id={item.route_stop_id} not found on route {route_id}."})
        stops_to_update.append((stop, item.new_sequence_order))
    
    # Step 1: Negate sequence orders to avoid unique constraint violations during swap
    for stop, _ in stops_to_update:
        stop.sequence_order = -stop.id
    
    await db.commit()
    
    # Step 2: Set the actual new sequence orders
    for stop, new_seq in stops_to_update:
        stop.sequence_order = new_seq
        
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail={"code": "REORDER_FAILED", "message": str(e)})
        
    route = await _load_route(db, route_id)
    return APIResponse(success=True, data=RouteResponse.model_validate(route))
