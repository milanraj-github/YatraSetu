"""
Admin: Driver management and bus assignment endpoints.

GET    /api/v1/drivers                          — List all drivers
GET    /api/v1/drivers/{driver_id}              — Get driver detail + current assignment
POST   /api/v1/drivers/{driver_id}/assign-bus   — Assign a bus to a driver (Admin)
DELETE /api/v1/drivers/{driver_id}/assign-bus   — Remove bus assignment (Admin)
GET    /api/v1/drivers/{driver_id}/assignments  — History of assignments (Admin)
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.schemas.auth import APIResponse, UserRole
from app.schemas.management import DriverResponse, AssignBusRequest, DriverAssignmentResponse, BusResponse

from app.models.route import Route, RouteStop
from app.models.schedule import TrackingSession
from app.services.scheduler_service import evaluate_scheduled_sessions_for_db, get_kolkata_today
from app.api.v1.tracking import get_db_user_from_auth

from pydantic import BaseModel
from typing import List, Optional


from app.models.route import RouteDirection
from datetime import time, datetime

class DriverBusSummary(BaseModel):
    bus_number: str
    registration_number: str
    capacity: int

class DriverBoardingPointSummary(BaseModel):
    name: str
    latitude: float
    longitude: float

class DriverRouteStopSummary(BaseModel):
    sequence_order: int
    boarding_point: DriverBoardingPointSummary

class DriverRouteSummary(BaseModel):
    name: str
    code: str
    stops: List[DriverRouteStopSummary] = []

class DriverScheduleSummary(BaseModel):
    start_time: time
    end_time: time
    direction: RouteDirection

from typing import Optional
class DriverSessionSummary(BaseModel):
    status: str
    direction: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

class TodayScheduleResponse(BaseModel):
    id: int
    bus: DriverBusSummary
    session: DriverSessionSummary
    schedule: DriverScheduleSummary
    route: DriverRouteSummary


from app.models.user import User, UserRole as DBUserRole
from app.models.driver_assignment import DriverBusAssignment, AssignmentStatus
from app.models.bus import Bus

logger = logging.getLogger("smartbus.drivers")
router = APIRouter(prefix="/drivers", tags=["Driver Management"])


async def _get_driver_or_404(db: AsyncSession, driver_id: int) -> User:
    result = await db.execute(
        select(User).where(User.id == driver_id, User.role == DBUserRole.DRIVER)
    )
    driver = result.scalars().first()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DRIVER_NOT_FOUND", "message": f"Driver with id={driver_id} not found."},
        )
    return driver


@router.get("", response_model=APIResponse[List[DriverResponse]])
async def list_drivers(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """List all users with DRIVER role. Admin only."""
    result = await db.execute(
        select(User).where(User.role == DBUserRole.DRIVER).order_by(User.id)
    )
    drivers = result.scalars().all()
    return APIResponse(success=True, data=[DriverResponse.model_validate(d) for d in drivers])



class DriverAssignmentDetailResponse(DriverAssignmentResponse):
    driver: DriverResponse
    bus: BusResponse

@router.get("/assignments/all", response_model=APIResponse[List[DriverAssignmentDetailResponse]])
async def get_all_assignments(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """Get all active driver-bus assignments. Admin only."""
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(DriverBusAssignment)
        .options(selectinload(DriverBusAssignment.driver), selectinload(DriverBusAssignment.bus).selectinload(Bus.route))
        .where(DriverBusAssignment.status == AssignmentStatus.ACTIVE)
        .order_by(DriverBusAssignment.assigned_from.desc())
    )
    assignments = result.scalars().all()
    return APIResponse(success=True, data=[DriverAssignmentDetailResponse.model_validate(a) for a in assignments])

@router.get("/{driver_id}", response_model=APIResponse[dict])
async def get_driver(driver_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """Get a driver's profile and their current active bus assignment."""
    driver = await _get_driver_or_404(db, driver_id)

    # Fetch current active assignment
    result = await db.execute(
        select(DriverBusAssignment).where(
            DriverBusAssignment.driver_id == driver_id,
            DriverBusAssignment.status == AssignmentStatus.ACTIVE,
        )
    )
    assignment = result.scalars().first()

    return APIResponse(
        success=True,
        data={
            "driver": DriverResponse.model_validate(driver),
            "current_assignment": DriverAssignmentResponse.model_validate(assignment) if assignment else None,
        },
    )


@router.post("/{driver_id}/assign-bus", response_model=APIResponse[DriverAssignmentResponse])
async def assign_bus(
    driver_id: int,
    payload: AssignBusRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """
    Assign a bus to a driver.
    - Deactivates any existing active assignment for this driver.
    - Creates a new ACTIVE assignment.
    Admin only.
    """
    driver = await _get_driver_or_404(db, driver_id)

    # Verify bus exists
    bus_result = await db.execute(select(Bus).where(Bus.id == payload.bus_id))
    bus = bus_result.scalars().first()
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BUS_NOT_FOUND", "message": f"Bus id={payload.bus_id} not found."},
        )

    # Deactivate existing active assignments for this driver
    existing_result = await db.execute(
        select(DriverBusAssignment).where(
            DriverBusAssignment.driver_id == driver_id,
            DriverBusAssignment.status == AssignmentStatus.ACTIVE,
        )
    )
    for existing in existing_result.scalars().all():
        existing.status = AssignmentStatus.INACTIVE
        logger.info(f"Deactivated old assignment id={existing.id} for driver {driver_id}")

    # Also deactivate any other driver currently assigned to this bus
    conflicting_result = await db.execute(
        select(DriverBusAssignment).where(
            DriverBusAssignment.bus_id == payload.bus_id,
            DriverBusAssignment.status == AssignmentStatus.ACTIVE,
            DriverBusAssignment.driver_id != driver_id,
        )
    )
    for conflicting in conflicting_result.scalars().all():
        conflicting.status = AssignmentStatus.INACTIVE
        logger.info(f"Deactivated conflicting assignment id={conflicting.id} on bus {payload.bus_id}")

    # Create new assignment
    assignment = DriverBusAssignment(
        driver_id=driver_id,
        bus_id=payload.bus_id,
        assigned_until=payload.assigned_until,
        status=AssignmentStatus.ACTIVE,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    logger.info(f"Driver {driver_id} assigned to bus {payload.bus_id} (assignment id={assignment.id})")
    return APIResponse(success=True, data=DriverAssignmentResponse.model_validate(assignment))


@router.delete("/{driver_id}/assign-bus", response_model=APIResponse[dict])
async def unassign_bus(driver_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """Remove the active bus assignment for a driver. Admin only."""
    driver = await _get_driver_or_404(db, driver_id)

    result = await db.execute(
        select(DriverBusAssignment).where(
            DriverBusAssignment.driver_id == driver_id,
            DriverBusAssignment.status == AssignmentStatus.ACTIVE,
        )
    )
    assignment = result.scalars().first()
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NO_ACTIVE_ASSIGNMENT", "message": f"Driver id={driver_id} has no active bus assignment."},
        )

    assignment.status = AssignmentStatus.INACTIVE
    await db.commit()
    return APIResponse(success=True, data={"message": f"Bus assignment deactivated for driver {driver_id}."})


@router.get("/{driver_id}/assignments", response_model=APIResponse[List[DriverAssignmentResponse]])
async def get_assignment_history(driver_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """Full assignment history for a driver. Admin only."""
    await _get_driver_or_404(db, driver_id)
    result = await db.execute(
        select(DriverBusAssignment)
        .where(DriverBusAssignment.driver_id == driver_id)
        .order_by(DriverBusAssignment.assigned_from.desc())
    )
    assignments = result.scalars().all()
    return APIResponse(success=True, data=[DriverAssignmentResponse.model_validate(a) for a in assignments])


@router.get("/me/schedules/today", response_model=APIResponse[List[TodayScheduleResponse]])
async def get_my_schedules_today(db: AsyncSession = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Only drivers can access their schedules."},
        )

    db_driver = await get_db_user_from_auth(db, current_user)
    await evaluate_scheduled_sessions_for_db(db)
    
    today_date = get_kolkata_today()
    
    stmt = select(TrackingSession).options(
        selectinload(TrackingSession.bus),
        selectinload(TrackingSession.schedule),
        selectinload(TrackingSession.route).selectinload(Route.stops).selectinload(RouteStop.boarding_point)
    ).where(
        TrackingSession.driver_id == db_driver.id,
        TrackingSession.session_date == today_date
    ).order_by(TrackingSession.id.asc())
    
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    
    data = []
    for session in sessions:
        data.append(TodayScheduleResponse(
            id=session.id,
            bus=DriverBusSummary(
                bus_number=session.bus.bus_number,
                registration_number=session.bus.registration_number,
                capacity=session.bus.capacity
            ),
            session=DriverSessionSummary(
                status=session.status.value,
                direction=session.direction.value,
                started_at=session.started_at,
                ended_at=session.ended_at
            ),
            schedule=DriverScheduleSummary(
                start_time=session.schedule.start_time,
                end_time=session.schedule.end_time,
                direction=session.schedule.direction
            ),
            route=DriverRouteSummary(
                name=session.route.name,
                code=session.route.code,
                stops=[DriverRouteStopSummary(
                    sequence_order=stop.sequence_order,
                    boarding_point=DriverBoardingPointSummary(
                        name=stop.boarding_point.name,
                        latitude=stop.boarding_point.latitude,
                        longitude=stop.boarding_point.longitude
                    )
                ) for stop in sorted(session.route.stops, key=lambda s: s.sequence_order)]
            )
        ))
        
    return APIResponse(success=True, data=data)


from app.services.scheduler_service import get_kolkata_now
from app.models.schedule import SessionStatus

@router.post("/me/sessions/{session_id}/start", response_model=APIResponse[TodayScheduleResponse])
async def start_trip(session_id: int, db: AsyncSession = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
    if current_user.role != DBUserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Only drivers can start trips."},
        )
    db_driver = await get_db_user_from_auth(db, current_user)
    
    # 1. Ensure duplicate start protection - check if there's ALREADY an ACTIVE session for this driver
    stmt_active = select(TrackingSession).where(
        TrackingSession.driver_id == db_driver.id,
        TrackingSession.status == SessionStatus.ACTIVE
    )
    res_active = await db.execute(stmt_active)
    active_session = res_active.scalars().first()
    
    # 2. Get the requested session
    stmt_session = select(TrackingSession).options(
        selectinload(TrackingSession.bus),
        selectinload(TrackingSession.schedule),
        selectinload(TrackingSession.route).selectinload(Route.stops).selectinload(RouteStop.boarding_point)
    ).where(TrackingSession.id == session_id)
    res_session = await db.execute(stmt_session)
    session = res_session.scalars().first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Trip or schedule not found."}
        )
        
    if session.driver_id != db_driver.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "You are not authorized to manage this trip."}
        )
        
    if session.status == SessionStatus.ACTIVE:
        # Already active, idempotent return
        pass
    elif session.status == SessionStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": "This trip is already completed."}
        )
    elif session.status == SessionStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "UNPROCESSABLE", "message": "Trip cannot be started with the current schedule."}
        )
    else:
        if active_session and active_session.id != session.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "CONFLICT", "message": "You already have another active trip."}
            )
        # Transition to ACTIVE
        session.status = SessionStatus.ACTIVE
        session.started_at = get_kolkata_now()
        await db.commit()
        await db.refresh(session)
        
        from app.services.notification_service import notify_students
        from app.models.notification import NotificationPriority
        await notify_students(
            db=db,
            bus_id=session.bus_id,
            event_type="BUS_TRIP_STARTED",
            title=f"{session.bus.bus_number} Trip Started",
            message=f"Your assigned bus has started its trip.",
            priority=NotificationPriority.NORMAL,
            related_entity_id=session.id
        )
        
    # Build response
    resp_data = TodayScheduleResponse(
        id=session.id,
        bus=DriverBusSummary(
            bus_number=session.bus.bus_number,
            registration_number=session.bus.registration_number,
            capacity=session.bus.capacity
        ),
        session=DriverSessionSummary(
                status=session.status.value,
                direction=session.direction.value,
                started_at=session.started_at,
                ended_at=session.ended_at
            ),
        schedule=DriverScheduleSummary(
            start_time=session.schedule.start_time,
            end_time=session.schedule.end_time,
            direction=session.schedule.direction
        ),
        route=DriverRouteSummary(
            name=session.route.name,
            code=session.route.code,
            stops=[DriverRouteStopSummary(
                sequence_order=stop.sequence_order,
                boarding_point=DriverBoardingPointSummary(
                    name=stop.boarding_point.name,
                    latitude=stop.boarding_point.latitude,
                    longitude=stop.boarding_point.longitude
                )
            ) for stop in sorted(session.route.stops, key=lambda s: s.sequence_order)]
        )
    )
    return APIResponse(success=True, data=resp_data)

@router.post("/me/sessions/{session_id}/end", response_model=APIResponse[TodayScheduleResponse])
async def end_trip(session_id: int, db: AsyncSession = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
    if current_user.role != DBUserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Only drivers can end trips."},
        )
    db_driver = await get_db_user_from_auth(db, current_user)
    
    # 1. Get the requested session
    stmt_session = select(TrackingSession).options(
        selectinload(TrackingSession.bus),
        selectinload(TrackingSession.schedule),
        selectinload(TrackingSession.route).selectinload(Route.stops).selectinload(RouteStop.boarding_point)
    ).where(TrackingSession.id == session_id)
    res_session = await db.execute(stmt_session)
    session = res_session.scalars().first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Trip or schedule not found."}
        )
        
    if session.driver_id != db_driver.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "You are not authorized to manage this trip."}
        )
        
    if session.status == SessionStatus.COMPLETED:
        # Already completed, idempotent return
        pass
    elif session.status != SessionStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "UNPROCESSABLE", "message": "Only active trips can be ended."}
        )
    else:
        # Transition to COMPLETED
        session.status = SessionStatus.COMPLETED
        session.ended_at = get_kolkata_now()
        await db.commit()
        await db.refresh(session)
        
        from app.services.notification_service import notify_students
        from app.models.notification import NotificationPriority
        await notify_students(
            db=db,
            bus_id=session.bus_id,
            event_type="BUS_TRIP_ENDED",
            title=f"{session.bus.bus_number} Trip Ended",
            message=f"Your assigned bus has reached its final destination.",
            priority=NotificationPriority.NORMAL,
            related_entity_id=session.id
        )
        
    # Build response
    resp_data = TodayScheduleResponse(
        id=session.id,
        bus=DriverBusSummary(
            bus_number=session.bus.bus_number,
            registration_number=session.bus.registration_number,
            capacity=session.bus.capacity
        ),
        session=DriverSessionSummary(
                status=session.status.value,
                direction=session.direction.value,
                started_at=session.started_at,
                ended_at=session.ended_at
            ),
        schedule=DriverScheduleSummary(
            start_time=session.schedule.start_time,
            end_time=session.schedule.end_time,
            direction=session.schedule.direction
        ),
        route=DriverRouteSummary(
            name=session.route.name,
            code=session.route.code,
            stops=[DriverRouteStopSummary(
                sequence_order=stop.sequence_order,
                boarding_point=DriverBoardingPointSummary(
                    name=stop.boarding_point.name,
                    latitude=stop.boarding_point.latitude,
                    longitude=stop.boarding_point.longitude
                )
            ) for stop in sorted(session.route.stops, key=lambda s: s.sequence_order)]
        )
    )
    return APIResponse(success=True, data=resp_data)

@router.get("/me/history", response_model=APIResponse[List[TodayScheduleResponse]])
async def get_driver_history(
    limit: int = Query(20, description="Max history limit"),
    db: AsyncSession = Depends(get_db), 
    current_user: UserResponse = Depends(get_current_user)
):
    if current_user.role != DBUserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Only drivers can access trip history."},
        )
    db_driver = await get_db_user_from_auth(db, current_user)
    
    # Get COMPLETED trips
    stmt = select(TrackingSession).options(
        selectinload(TrackingSession.bus),
        selectinload(TrackingSession.schedule),
        selectinload(TrackingSession.route).selectinload(Route.stops).selectinload(RouteStop.boarding_point)
    ).where(
        TrackingSession.driver_id == db_driver.id,
        TrackingSession.status == SessionStatus.COMPLETED
    ).order_by(TrackingSession.ended_at.desc()).limit(limit)
    
    res = await db.execute(stmt)
    sessions = res.scalars().all()
    
    data = []
    for session in sessions:
        data.append(TodayScheduleResponse(
            id=session.id,
            bus=DriverBusSummary(
                bus_number=session.bus.bus_number,
                registration_number=session.bus.registration_number,
                capacity=session.bus.capacity
            ),
            session=DriverSessionSummary(
                status=session.status.value,
                direction=session.direction.value,
                started_at=session.started_at,
                ended_at=session.ended_at
            ),
            schedule=DriverScheduleSummary(
                start_time=session.schedule.start_time,
                end_time=session.schedule.end_time,
                direction=session.schedule.direction
            ),
            route=DriverRouteSummary(
                name=session.route.name,
                code=session.route.code,
                stops=[DriverRouteStopSummary(
                    sequence_order=stop.sequence_order,
                    boarding_point=DriverBoardingPointSummary(
                        name=stop.boarding_point.name,
                        latitude=stop.boarding_point.latitude,
                        longitude=stop.boarding_point.longitude
                    )
                ) for stop in sorted(session.route.stops, key=lambda s: s.sequence_order)]
            )
        ))
        
    return APIResponse(success=True, data=data)
