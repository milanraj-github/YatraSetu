from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.schemas.auth import UserResponse, APIResponse
from app.dependencies.auth import require_parent
from app.models.user import User, UserStatus, UserRole
from app.models.parent_student_relationship import ParentStudentRelationship, RelationshipStatus
from app.models.student_assignment import StudentBusAssignment, StudentAssignmentStatus
from app.models.bus import Bus
from app.api.v1.students import StudentTripHistoryResponse, StudentTripItem, StudentTripBusSummary, StudentTripRouteSummary
from app.models.emergency import Emergency, EmergencyStatus
from app.models.alert import Alert, AlertStatus

router = APIRouter(prefix="/parents/me", tags=["Parent Portal"])

@router.get("/students", response_model=APIResponse)
async def get_my_students(
    db: AsyncSession = Depends(get_db),
    current_parent: UserResponse = Depends(require_parent)
):
    """
    Get all ACTIVE students linked to the authenticated parent,
    along with their current bus assignment.
    """
    # 1. Resolve DB User ID from current_parent
    stmt = select(User).where(User.email == current_parent.email, User.role == UserRole.PARENT)
    res = await db.execute(stmt)
    db_parent = res.scalars().first()
    
    if not db_parent:
        raise HTTPException(status_code=404, detail="Parent account not found.")

    # 2. Fetch ACTIVE relationships
    rel_stmt = (
        select(ParentStudentRelationship)
        .where(
            ParentStudentRelationship.parent_id == db_parent.id,
            ParentStudentRelationship.status == RelationshipStatus.ACTIVE
        )
        .options(selectinload(ParentStudentRelationship.student))
    )
    rel_res = await db.execute(rel_stmt)
    relationships = rel_res.scalars().all()
    
    result_data = []
    
    for rel in relationships:
        student = rel.student
        if student.status != UserStatus.ACTIVE:
            continue
            
        # Fetch Student Bus Assignment
        assignment_stmt = (
            select(StudentBusAssignment)
            .where(
                StudentBusAssignment.student_id == student.id,
                StudentBusAssignment.status == StudentAssignmentStatus.ACTIVE
            )
            .options(selectinload(StudentBusAssignment.bus))
            .order_by(StudentBusAssignment.created_at.desc())
        )
        assignment_res = await db.execute(assignment_stmt)
        assignment = assignment_res.scalars().first()
        
        bus_info = None
        if assignment and assignment.bus:
            bus_info = {
                "id": assignment.bus.id,
                "bus_number": assignment.bus.bus_number,
                "registration_number": assignment.bus.registration_number,
                "status": assignment.bus.status.value if hasattr(assignment.bus.status, 'value') else assignment.bus.status
            }
            
        result_data.append({
            "relationship_id": rel.id,
            "relationship_type": rel.relationship_type.value,
            "student": {
                "id": student.id,
                "full_name": student.full_name,
                "email": student.email,
                "status": student.status.value,
            },
            "bus": bus_info
        })

    return APIResponse(success=True, data={"students": result_data})

from app.api.v1.students import StudentLiveBusResponse, StudentBusResponse
from app.models.student_assignment import StudentAssignmentStatus
from app.models.schedule import TrackingSession, SessionStatus
from app.schemas.tracking import LocationPointSchema
from app.core.redis import get_redis_json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.services.tracking_service import calculate_stop_intelligence, calculate_eta

@router.get("/{student_id}/live-bus", response_model=APIResponse)
async def get_parent_student_live_bus(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_parent: UserResponse = Depends(require_parent)
):
    """
    Get live bus tracking for a specific authorized student.
    """
    # 1. Resolve Parent DB Identity
    stmt = select(User).where(User.email == current_parent.email, User.role == UserRole.PARENT)
    db_parent = (await db.execute(stmt)).scalars().first()
    if not db_parent:
        raise HTTPException(status_code=404, detail="Parent account not found.")

    # 2. Verify Authorized Relationship
    rel_stmt = select(ParentStudentRelationship).where(
        ParentStudentRelationship.parent_id == db_parent.id,
        ParentStudentRelationship.student_id == student_id,
        ParentStudentRelationship.status == RelationshipStatus.ACTIVE
    )
    rel = (await db.execute(rel_stmt)).scalars().first()
    if not rel:
        raise HTTPException(status_code=403, detail="You do not have active access to this student.")

    # 3. Fetch Student Bus Assignment
    assignment_stmt = (
        select(StudentBusAssignment)
        .options(selectinload(StudentBusAssignment.bus))
        .where(StudentBusAssignment.student_id == student_id)
        .where(StudentBusAssignment.status == StudentAssignmentStatus.ACTIVE)
        .order_by(StudentBusAssignment.created_at.desc())
    )
    assignment = (await db.execute(assignment_stmt)).scalars().first()

    if not assignment or not assignment.bus:
        return APIResponse(success=True, data=StudentLiveBusResponse(
            assigned=False, bus=None, trip=None, route=None, direction=None, location=None, tracking_status="UNAVAILABLE", stop_intelligence=None, eta=None
        ).model_dump())

    bus = assignment.bus
    bus_resp = StudentBusResponse(
        id=bus.id, bus_number=bus.bus_number, registration_number=bus.registration_number,
        capacity=bus.capacity, status=bus.status.value if hasattr(bus.status, 'value') else bus.status
    )

    # 4. Fetch Active Tracking Session
    stmt_trip = select(TrackingSession).options(selectinload(TrackingSession.route)).where(
        TrackingSession.bus_id == bus.id,
        TrackingSession.status == SessionStatus.ACTIVE
    )
    active_trip = (await db.execute(stmt_trip)).scalars().first()

    if not active_trip:
        return APIResponse(success=True, data=StudentLiveBusResponse(
            assigned=True, bus=bus_resp, trip=None, route=None, direction=None, location=None, tracking_status="NO_ACTIVE_TRIP", stop_intelligence=None, eta={"status": "NO_ACTIVE_TRIP"}
        ).model_dump())

    # 5. Fetch Live Redis Data
    redis_key = f"bus:{bus.id}:latest_location"
    redis_data = await get_redis_json(redis_key)

    if not redis_data:
        return APIResponse(success=True, data=StudentLiveBusResponse(
            assigned=True, bus=bus_resp, 
            trip={"id": active_trip.id, "status": active_trip.status.value}, 
            route={"id": active_trip.route.id, "name": active_trip.route.name} if active_trip.route else None,
            direction=active_trip.direction.value if active_trip.direction else None,
            location=None, tracking_status="NO_LOCATION", stop_intelligence=None, eta={"status": "NO_LOCATION"}
        ).model_dump())

    loc = LocationPointSchema(**redis_data)
    
    # Staleness check
    now = datetime.now(timezone.utc).timestamp()
    recorded = loc.recorded_at.timestamp()
    is_stale = (now - recorded) > 60  # 60 seconds threshold

    status = "STALE" if is_stale else "LIVE"

    stop_intelligence = await calculate_stop_intelligence(db, active_trip.id, bus.id, loc.latitude, loc.longitude)

    eta_data = {"status": "UNAVAILABLE"}
    if status == "STALE":
        eta_data = {"status": "STALE"}
    elif stop_intelligence and stop_intelligence.get("next_stop"):
        eta_data = await calculate_eta(db, active_trip.id, loc.latitude, loc.longitude, loc.speed, stop_intelligence["next_stop"])
    elif stop_intelligence and stop_intelligence.get("status") == "TRIP_COMPLETED_AT_DESTINATION":
        eta_data = {"status": "ARRIVED"}
    else:
        eta_data = {"status": "NO_NEXT_STOP"}

    return APIResponse(success=True, data=StudentLiveBusResponse(
        assigned=True, bus=bus_resp, 
        trip={"id": active_trip.id, "status": active_trip.status.value}, 
        route={"id": active_trip.route.id, "name": active_trip.route.name} if active_trip.route else None,
        direction=active_trip.direction.value if active_trip.direction else None,
        location=loc, tracking_status=status, stop_intelligence=stop_intelligence, eta=eta_data
    ).model_dump())


@router.get("/safety", response_model=APIResponse)
async def get_my_safety_events(
    db: AsyncSession = Depends(get_db),
    current_parent: UserResponse = Depends(require_parent)
):
    stmt = select(User).where(User.email == current_parent.email, User.role == UserRole.PARENT)
    res = await db.execute(stmt)
    db_parent = res.scalars().first()
    
    if not db_parent:
        raise HTTPException(status_code=404, detail="Parent account not found.")

    from app.api.v1.parents_me_safety import get_parent_safety_events
    data = await get_parent_safety_events(db, db_parent)
    
    return APIResponse(success=True, data=data)


@router.get("/{student_id}/trips/history", response_model=APIResponse[StudentTripHistoryResponse])
async def get_parent_student_trip_history(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_parent: UserResponse = Depends(require_parent),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    from app.services.scheduler_service import get_kolkata_now
    from app.models.schedule import TrackingSession, SessionStatus
    import pytz
    
    # 1. Resolve Parent DB Identity
    stmt = select(User).where(User.email == current_parent.email, User.role == UserRole.PARENT)
    res = await db.execute(stmt)
    db_parent = res.scalars().first()
    
    if not db_parent:
        raise HTTPException(status_code=404, detail="Parent account not found.")

    # 2. Check ACTIVE relationship
    rel_stmt = select(ParentStudentRelationship).where(
        ParentStudentRelationship.parent_id == db_parent.id,
        ParentStudentRelationship.student_id == student_id,
        ParentStudentRelationship.status == RelationshipStatus.ACTIVE
    )
    rel_res = await db.execute(rel_stmt)
    if not rel_res.scalars().first():
        raise HTTPException(status_code=403, detail="Not authorized to access this student's history.")

    # Fetch ALL assignments for this student (both active and inactive historical)
    stmt_assignments = (
        select(StudentBusAssignment)
        .where(StudentBusAssignment.student_id == student_id)
        .order_by(StudentBusAssignment.assigned_from)
    )
    res_assignments = await db.execute(stmt_assignments)
    assignments = res_assignments.scalars().all()

    if not assignments:
        return APIResponse(success=True, data=StudentTripHistoryResponse(
            items=[], page=page, page_size=page_size, total=0
        ))

    # Collect all bus_ids from student assignments
    bus_ids = list({a.bus_id for a in assignments})

    # Fetch candidate COMPLETED/CANCELLED trips for those buses
    stmt_trips = (
        select(TrackingSession)
        .options(
            selectinload(TrackingSession.bus),
            selectinload(TrackingSession.route),
        )
        .where(
            TrackingSession.bus_id.in_(bus_ids),
            TrackingSession.status.in_([SessionStatus.COMPLETED, SessionStatus.CANCELLED]),
            TrackingSession.started_at.isnot(None),
        )
        .order_by(TrackingSession.started_at.desc())
    )
    res_trips = await db.execute(stmt_trips)
    candidate_trips = res_trips.scalars().all()

    seen_trip_ids: set = set()
    matching_trips = []

    for trip in candidate_trips:
        if trip.id in seen_trip_ids:
            continue
        trip_started = trip.started_at
        for a in assignments:
            if a.bus_id != trip.bus_id:
                continue
            
            a_from = a.assigned_from
            a_until = a.assigned_until

            if trip_started.tzinfo is None:
                a_from = a_from.replace(tzinfo=None) if a_from.tzinfo else a_from
                a_until = a_until.replace(tzinfo=None) if (a_until and a_until.tzinfo) else a_until
            else:
                from datetime import timezone as tz_module
                if a_from.tzinfo is None:
                    a_from = a_from.replace(tzinfo=tz_module.utc)
                if a_until and a_until.tzinfo is None:
                    a_until = a_until.replace(tzinfo=tz_module.utc)

            if trip_started >= a_from and (a_until is None or trip_started <= a_until):
                seen_trip_ids.add(trip.id)
                matching_trips.append(trip)
                break

    total = len(matching_trips)
    offset = (page - 1) * page_size
    page_trips = matching_trips[offset: offset + page_size]

    kolkata_tz = pytz.timezone("Asia/Kolkata")
    items = []
    for trip in page_trips:
        started = trip.started_at
        ended = trip.ended_at

        if started:
            started_local = started.astimezone(kolkata_tz) if started.tzinfo else started
            date_str = started_local.strftime("%Y-%m-%d")
        else:
            date_str = "Unknown"

        duration_seconds = None
        if started and ended:
            delta = ended - started
            duration_seconds = int(delta.total_seconds())

        items.append(StudentTripItem(
            trip_id=trip.id,
            date=date_str,
            bus=StudentTripBusSummary(
                id=trip.bus.id,
                bus_number=trip.bus.bus_number,
                registration_number=trip.bus.registration_number,
            ),
            route=StudentTripRouteSummary(
                id=trip.route.id,
                name=trip.route.name,
                code=trip.route.code,
            ),
            direction=trip.direction.value,
            status=trip.status.value,
            started_at=started,
            ended_at=ended,
            duration_seconds=duration_seconds,
        ))

    return APIResponse(success=True, data=StudentTripHistoryResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
    ))
