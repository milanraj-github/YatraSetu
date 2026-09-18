"""
Admin: Schedule management endpoints.

GET    /api/v1/schedules                  — List all schedules (all roles)
POST   /api/v1/schedules                  — Create a schedule (Admin)
GET    /api/v1/schedules/{schedule_id}    — Get a schedule (all roles)
PATCH  /api/v1/schedules/{schedule_id}    — Update schedule (Admin)
DELETE /api/v1/schedules/{schedule_id}    — Delete schedule (Admin)

Trip/Session queries (read-only for all authenticated roles):
GET    /api/v1/trips                      — List tracking sessions (filter by status, date, bus)
GET    /api/v1/trips/{trip_id}            — Get a single tracking session
"""
import logging
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.schemas.auth import APIResponse
from app.schemas.management import ScheduleCreate, ScheduleUpdate, ScheduleResponse, TripResponse
from app.models.schedule import TripSchedule, TrackingSession, SessionStatus
from app.models.bus import Bus
from app.models.route import Route

logger = logging.getLogger("smartbus.schedules")

schedules_router = APIRouter(prefix="/schedules", tags=["Schedules"])
trips_router = APIRouter(prefix="/trips", tags=["Trips"])


# ─────────────────────────────────────────────────────────────────────────────
# SCHEDULES
# ─────────────────────────────────────────────────────────────────────────────

async def _get_schedule_or_404(db: AsyncSession, schedule_id: int) -> TripSchedule:
    result = await db.execute(select(TripSchedule).where(TripSchedule.id == schedule_id))
    sched = result.scalars().first()
    if not sched:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SCHEDULE_NOT_FOUND", "message": f"Schedule id={schedule_id} not found."},
        )
    return sched


@schedules_router.get("", response_model=APIResponse[List[ScheduleResponse]])
async def list_schedules(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(TripSchedule).order_by(TripSchedule.id))
    return APIResponse(success=True, data=[ScheduleResponse.model_validate(s) for s in result.scalars().all()])


@schedules_router.post("", response_model=APIResponse[ScheduleResponse], status_code=status.HTTP_201_CREATED)
async def create_schedule(payload: ScheduleCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """Create a trip schedule for a bus on a route. Admin only."""
    # Validate bus and route exist
    bus = await db.execute(select(Bus).where(Bus.id == payload.bus_id))
    if not bus.scalars().first():
        raise HTTPException(status_code=422, detail={"code": "BUS_NOT_FOUND", "message": f"Bus id={payload.bus_id} not found."})
    route = await db.execute(select(Route).where(Route.id == payload.route_id))
    if not route.scalars().first():
        raise HTTPException(status_code=422, detail={"code": "ROUTE_NOT_FOUND", "message": f"Route id={payload.route_id} not found."})

    from app.models.route import RouteDirection
    sched = TripSchedule(
        bus_id=payload.bus_id,
        route_id=payload.route_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        direction=RouteDirection(payload.direction.value),
        days_of_week=payload.days_of_week,
        active=True,
    )
    db.add(sched)
    await db.commit()
    await db.refresh(sched)
    logger.info(f"Schedule created: bus {sched.bus_id} route {sched.route_id} (id={sched.id})")
    return APIResponse(success=True, data=ScheduleResponse.model_validate(sched))


@schedules_router.get("/{schedule_id}", response_model=APIResponse[ScheduleResponse])
async def get_schedule(schedule_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    sched = await _get_schedule_or_404(db, schedule_id)
    return APIResponse(success=True, data=ScheduleResponse.model_validate(sched))


@schedules_router.patch("/{schedule_id}", response_model=APIResponse[ScheduleResponse])
async def update_schedule(schedule_id: int, payload: ScheduleUpdate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """Update schedule times, days, or active flag. Admin only."""
    sched = await _get_schedule_or_404(db, schedule_id)
    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(sched, field, val)
    await db.commit()
    await db.refresh(sched)
    return APIResponse(success=True, data=ScheduleResponse.model_validate(sched))


@schedules_router.delete("/{schedule_id}", response_model=APIResponse[dict])
async def delete_schedule(schedule_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    sched = await _get_schedule_or_404(db, schedule_id)
    await db.delete(sched)
    await db.commit()
    return APIResponse(success=True, data={"message": f"Schedule id={schedule_id} deleted."})


# ─────────────────────────────────────────────────────────────────────────────
# TRIPS (Tracking Sessions — read-only for all roles)
# ─────────────────────────────────────────────────────────────────────────────

@trips_router.get("", response_model=APIResponse[List[TripResponse]])
async def list_trips(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
    trip_status: Optional[str] = Query(default=None, description="Filter by status: SCHEDULED, ACTIVE, COMPLETED, CANCELLED"),
    bus_id: Optional[int] = Query(default=None, description="Filter by bus ID"),
    session_date: Optional[date] = Query(default=None, description="Filter by date (YYYY-MM-DD)"),
    limit: int = Query(default=50, ge=1, le=200),
):
    """List tracking sessions with optional filters. All authenticated roles."""
    stmt = select(TrackingSession).order_by(TrackingSession.id.desc()).limit(limit)

    if trip_status:
        try:
            status_filter = SessionStatus(trip_status.upper())
            stmt = stmt.where(TrackingSession.status == status_filter)
        except ValueError:
            raise HTTPException(status_code=422, detail={"code": "INVALID_STATUS", "message": f"Invalid status '{trip_status}'."})

    if bus_id is not None:
        stmt = stmt.where(TrackingSession.bus_id == bus_id)

    if session_date is not None:
        stmt = stmt.where(TrackingSession.session_date == session_date)

    result = await db.execute(stmt)
    trips = result.scalars().all()
    return APIResponse(success=True, data=[TripResponse.model_validate(t) for t in trips])


@trips_router.get("/{trip_id}", response_model=APIResponse[TripResponse])
async def get_trip(trip_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    """Get a single tracking session by ID."""
    result = await db.execute(select(TrackingSession).where(TrackingSession.id == trip_id))
    trip = result.scalars().first()
    if not trip:
        raise HTTPException(
            status_code=404,
            detail={"code": "TRIP_NOT_FOUND", "message": f"Trip id={trip_id} not found."},
        )
    return APIResponse(success=True, data=TripResponse.model_validate(trip))
