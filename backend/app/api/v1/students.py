from typing import List, Dict, Optional, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, and_
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.schemas.auth import UserResponse, APIResponse, UserRole
from app.dependencies.auth import get_current_user, require_admin, require_student
from app.models.user import User
from app.models.bus import Bus
from app.models.route import Route, RouteStop
from app.models.student_assignment import StudentBusAssignment, StudentAssignmentStatus
from pydantic import BaseModel

from app.models.schedule import TrackingSession, SessionStatus
from app.services.tracking_service import calculate_stop_intelligence, calculate_eta

from app.core.redis import get_redis_json
from app.schemas.tracking import LocationPointSchema
from datetime import timezone


router = APIRouter(prefix="/students", tags=["Students"])

class StudentBusAssignmentResponse(BaseModel):
    id: int
    assigned_from: datetime
    assigned_until: Optional[datetime]
    status: str
    
class StudentBusResponse(BaseModel):
    id: int
    bus_number: str
    registration_number: str
    capacity: int
    status: str

class StudentAssignmentDetails(BaseModel):
    assigned: bool
    bus: Optional[StudentBusResponse]
    assignment: Optional[StudentBusAssignmentResponse]

class AdminStudentListResponse(BaseModel):
    id: int
    full_name: str
    email: str
    status: str
    current_bus_number: Optional[str]




class StudentLiveBusResponse(BaseModel):
    assigned: bool
    bus: Optional[StudentBusResponse] = None
    trip: Optional[Dict[str, Any]] = None
    route: Optional[Dict[str, Any]] = None
    direction: Optional[str] = None
    location: Optional[LocationPointSchema] = None
    tracking_status: str
    stop_intelligence: Optional[Dict[str, Any]] = None
    eta: Optional[Dict[str, Any]] = None

class AdminAssignBusRequest(BaseModel):
    bus_id: int

@router.get("/me/bus", response_model=APIResponse[StudentAssignmentDetails])
async def get_my_bus(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(require_student)
):

    # Get DB user ID
    stmt_user = select(User).where(User.firebase_uid == current_user.firebase_uid)
    db_user = (await db.execute(stmt_user)).scalars().first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Student not found in DB")
        
    stmt = (
        select(StudentBusAssignment)
        .options(selectinload(StudentBusAssignment.bus))
        .where(StudentBusAssignment.student_id == db_user.id)
        .where(StudentBusAssignment.status == StudentAssignmentStatus.ACTIVE)
    )

    res = await db.execute(stmt)
    assignment = res.scalars().first()
    
    if not assignment:
        return APIResponse(success=True, data=StudentAssignmentDetails(assigned=False, bus=None, assignment=None))
        
    return APIResponse(success=True, data=StudentAssignmentDetails(
        assigned=True,
        bus=StudentBusResponse(
            id=assignment.bus.id,
            bus_number=assignment.bus.bus_number,
            registration_number=assignment.bus.registration_number,
            capacity=assignment.bus.capacity,
            status=assignment.bus.status.value
        ),
        assignment=StudentBusAssignmentResponse(
            id=assignment.id,
            assigned_from=assignment.assigned_from,
            assigned_until=assignment.assigned_until,
            status=assignment.status.value
        )
    ))

@router.get("", response_model=APIResponse[List[AdminStudentListResponse]])
async def list_students_admin(
    db: AsyncSession = Depends(get_db),
    admin: UserResponse = Depends(require_admin)
):
    # Get all students and their active assignment
    stmt = (
        select(User, StudentBusAssignment.bus_id, Bus.bus_number)
        .outerjoin(StudentBusAssignment, (StudentBusAssignment.student_id == User.id) & (StudentBusAssignment.status == StudentAssignmentStatus.ACTIVE))
        .outerjoin(Bus, Bus.id == StudentBusAssignment.bus_id)
        .where(User.role == 'STUDENT')
    )
    res = await db.execute(stmt)
    rows = res.all()
    
    data = []
    for user, bus_id, bus_number in rows:
        data.append(AdminStudentListResponse(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            status=user.status.value,
            current_bus_number=bus_number
        ))
        
    return APIResponse(success=True, data=data)

@router.post("/{student_id}/assignment", response_model=APIResponse[StudentAssignmentDetails])
async def admin_assign_bus(
    student_id: int,
    payload: AdminAssignBusRequest,
    db: AsyncSession = Depends(get_db),
    admin: UserResponse = Depends(require_admin)
):
    # Validate Student
    student = await db.get(User, student_id)
    if not student or student.role.value != 'STUDENT':
        raise HTTPException(status_code=404, detail="Student not found or not a valid student.")
        
    # Validate Bus
    bus = await db.get(Bus, payload.bus_id)
    if not bus:
        raise HTTPException(status_code=404, detail="Bus not found.")
        
    # Atomic deactivate old and create new
    stmt = (
        select(StudentBusAssignment)
        .where(StudentBusAssignment.student_id == student_id)
        .where(StudentBusAssignment.status == StudentAssignmentStatus.ACTIVE)
    )
    old_assignment = (await db.execute(stmt)).scalars().first()
    
    if old_assignment:
        if old_assignment.bus_id == payload.bus_id:
            raise HTTPException(status_code=400, detail="Student is already assigned to this bus.")
        old_assignment.status = StudentAssignmentStatus.INACTIVE
        old_assignment.assigned_until = datetime.utcnow()
        
    new_assignment = StudentBusAssignment(
        student_id=student_id,
        bus_id=payload.bus_id,
        status=StudentAssignmentStatus.ACTIVE
    )
    db.add(new_assignment)
    await db.commit()
    await db.refresh(new_assignment)
    
    return APIResponse(success=True, data=StudentAssignmentDetails(
        assigned=True,
        bus=StudentBusResponse(
            id=bus.id,
            bus_number=bus.bus_number,
            registration_number=bus.registration_number,
            capacity=bus.capacity,
            status=bus.status.value
        ),
        assignment=StudentBusAssignmentResponse(
            id=new_assignment.id,
            assigned_from=new_assignment.assigned_from,
            assigned_until=new_assignment.assigned_until,
            status=new_assignment.status.value
        )
    ))

@router.delete("/{student_id}/assignment", response_model=APIResponse[Dict[str, str]])
async def admin_remove_assignment(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    admin: UserResponse = Depends(require_admin)
):
    stmt = (
        select(StudentBusAssignment)
        .where(StudentBusAssignment.student_id == student_id)
        .where(StudentBusAssignment.status == StudentAssignmentStatus.ACTIVE)
    )
    assignment = (await db.execute(stmt)).scalars().first()
    
    if assignment:
        assignment.status = StudentAssignmentStatus.INACTIVE
        assignment.assigned_until = datetime.utcnow()
        await db.commit()
        
    return APIResponse(success=True, data={"message": "Assignment removed successfully."})



@router.get("/me/live-bus", response_model=APIResponse[StudentLiveBusResponse])
async def get_student_live_bus(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(require_student)
):
    stmt_user = select(User).where(User.firebase_uid == current_user.firebase_uid)
    db_user = (await db.execute(stmt_user)).scalars().first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Student not found in DB")
        
    stmt = (
        select(StudentBusAssignment)
        .options(selectinload(StudentBusAssignment.bus))
        .where(StudentBusAssignment.student_id == db_user.id)
        .where(StudentBusAssignment.status == StudentAssignmentStatus.ACTIVE)
    )
    assignment = (await db.execute(stmt)).scalars().first()
    
    if not assignment:
        return APIResponse(success=True, data=StudentLiveBusResponse(
            assigned=False, bus=None, trip=None, location=None, tracking_status="UNAVAILABLE"
        ))
        
    bus = assignment.bus
    
    # Check for active trip
    stmt_trip = select(TrackingSession).options(selectinload(TrackingSession.route)).where(
        TrackingSession.bus_id == bus.id,
        TrackingSession.status == SessionStatus.ACTIVE
    )
    active_trip = (await db.execute(stmt_trip)).scalars().first()
    
    bus_resp = StudentBusResponse(
        id=bus.id, bus_number=bus.bus_number, registration_number=bus.registration_number,
        capacity=bus.capacity, status=bus.status.value
    )
    
    if not active_trip:
        return APIResponse(success=True, data=StudentLiveBusResponse(
            assigned=True, bus=bus_resp, trip=None, route=None, direction=None, location=None, tracking_status="NO_ACTIVE_TRIP", stop_intelligence=None, eta={"status": "NO_ACTIVE_TRIP"}
        ))
        
    # Get live location from Redis
    redis_key = f"bus:{bus.id}:latest_location"
    redis_data = await get_redis_json(redis_key)
    
    if not redis_data:
        return APIResponse(success=True, data=StudentLiveBusResponse(
            assigned=True, bus=bus_resp, 
            trip={"id": active_trip.id, "status": active_trip.status.value}, 
            route={"id": active_trip.route.id, "name": active_trip.route.name} if active_trip.route else None,
            direction=active_trip.direction.value if active_trip.direction else None,
            location=None, tracking_status="UNAVAILABLE", stop_intelligence=None, eta={"status": "NO_LIVE_LOCATION"}
        ))
        
    location = LocationPointSchema(**redis_data)
    
    # Check if stale (e.g. older than 60 seconds)
    now = datetime.now(timezone.utc)
    recorded_at_aware = location.recorded_at.replace(tzinfo=timezone.utc) if location.recorded_at.tzinfo is None else location.recorded_at
    age_seconds = (now - recorded_at_aware).total_seconds()
    
    tracking_status = "LIVE"
    if age_seconds > 60:
        tracking_status = "STALE"
        
    
    stop_intelligence = await calculate_stop_intelligence(db, active_trip.id, bus.id, location.latitude, location.longitude)
    
    eta_data = {"status": "UNAVAILABLE"}
    if tracking_status == "STALE":
        eta_data = {"status": "STALE"}
    elif stop_intelligence and stop_intelligence.get("next_stop"):
        eta_data = await calculate_eta(db, active_trip.id, location.latitude, location.longitude, location.speed, stop_intelligence["next_stop"])
    elif stop_intelligence and stop_intelligence.get("status") == "TRIP_COMPLETED_AT_DESTINATION":
        eta_data = {"status": "ARRIVED"}
    else:
        eta_data = {"status": "NO_NEXT_STOP"}
    
    return APIResponse(success=True, data=StudentLiveBusResponse(
        assigned=True, bus=bus_resp, 
        trip={"id": active_trip.id, "status": active_trip.status.value},
        route={"id": active_trip.route.id, "name": active_trip.route.name} if active_trip.route else None,
        direction=active_trip.direction.value if active_trip.direction else None,
        location=location, tracking_status=tracking_status,
        stop_intelligence=stop_intelligence,
        eta=eta_data
    ))


# ─── S8 Student Trip History ─────────────────────────────────────────────────

class StudentTripBusSummary(BaseModel):
    id: int
    bus_number: str
    registration_number: str

class StudentTripRouteSummary(BaseModel):
    id: int
    name: str
    code: str

class StudentTripItem(BaseModel):
    trip_id: int
    date: str                        # ISO date in Kolkata TZ, e.g. "2026-09-19"
    bus: StudentTripBusSummary
    route: StudentTripRouteSummary
    direction: str
    status: str
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    duration_seconds: Optional[int]  # None when end time absent

class StudentTripHistoryResponse(BaseModel):
    items: List[StudentTripItem]
    page: int
    page_size: int
    total: int


@router.get("/me/trips/history", response_model=APIResponse[StudentTripHistoryResponse])
async def get_student_trip_history(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(require_student),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Returns historical trips relevant to the authenticated student.

    Relevance is determined by the student's bus assignments:
        A trip is relevant if:
          trip.bus_id == assignment.bus_id
          AND trip.started_at >= assignment.assigned_from
          AND (assignment.assigned_until IS NULL OR trip.started_at <= assignment.assigned_until)

    Only COMPLETED and CANCELLED trips are returned (not ACTIVE / SCHEDULED).
    Results are ordered newest first.
    """
    from app.services.scheduler_service import get_kolkata_now
    import pytz

    # Resolve student from Firebase UID
    stmt_user = select(User).where(User.firebase_uid == current_user.firebase_uid)
    db_user = (await db.execute(stmt_user)).scalars().first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Student not found.")

    student_id = db_user.id

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

    # Build a query that joins assignments to sessions via time-overlap.
    # We use a subquery-free approach: fetch all session IDs matching any assignment period.
    # For correctness we filter in Python after loading sessions with selectinload.
    # To avoid N+1, we fetch all candidate trips in one query then filter per-assignment.

    # Collect all bus_ids from student assignments
    bus_ids = list({a.bus_id for a in assignments})

    # Fetch candidate COMPLETED/CANCELLED trips for those buses (with eager loads)
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

    # Filter by assignment periods — a trip is valid if:
    # assignment.bus_id == trip.bus_id AND trip.started_at within assignment period
    seen_trip_ids: set = set()
    matching_trips: List[TrackingSession] = []

    for trip in candidate_trips:
        if trip.id in seen_trip_ids:
            continue
        trip_started = trip.started_at
        for a in assignments:
            if a.bus_id != trip.bus_id:
                continue
            # Make timestamps comparable (both UTC-aware or both naive)
            a_from = a.assigned_from
            a_until = a.assigned_until

            # Normalize: if trip_started is offset-naive, strip tz from bounds too
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
                break  # Found a valid assignment for this trip; stop checking others

    # Pagination
    total = len(matching_trips)
    offset = (page - 1) * page_size
    page_trips = matching_trips[offset: offset + page_size]

    # Build response items
    kolkata_tz = pytz.timezone("Asia/Kolkata")
    items: List[StudentTripItem] = []
    for trip in page_trips:
        started = trip.started_at
        ended = trip.ended_at

        # Format date in Kolkata TZ
        if started:
            started_local = started.astimezone(kolkata_tz) if started.tzinfo else started
            date_str = started_local.strftime("%Y-%m-%d")
        else:
            date_str = "Unknown"

        # Duration
        duration_seconds: Optional[int] = None
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


@router.get("/me/trips/{trip_id}", response_model=APIResponse[StudentTripItem])
async def get_student_trip_detail(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(require_student),
):
    """
    Returns detail for one historical trip, verifying the student had a valid
    bus assignment at the time of that trip. Prevents IDOR.
    """
    import pytz

    stmt_user = select(User).where(User.firebase_uid == current_user.firebase_uid)
    db_user = (await db.execute(stmt_user)).scalars().first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Student not found.")

    # Fetch trip with relationships
    stmt_trip = (
        select(TrackingSession)
        .options(selectinload(TrackingSession.bus), selectinload(TrackingSession.route))
        .where(TrackingSession.id == trip_id)
        .where(TrackingSession.status.in_([SessionStatus.COMPLETED, SessionStatus.CANCELLED]))
        .where(TrackingSession.started_at.isnot(None))
    )
    res_trip = await db.execute(stmt_trip)
    trip = res_trip.scalars().first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found.")

    # Verify student had a valid assignment for this bus at trip time
    trip_started = trip.started_at
    stmt_assign = (
        select(StudentBusAssignment)
        .where(
            StudentBusAssignment.student_id == db_user.id,
            StudentBusAssignment.bus_id == trip.bus_id,
        )
    )
    res_assign = await db.execute(stmt_assign)
    assignments = res_assign.scalars().all()

    authorized = False
    for a in assignments:
        a_from = a.assigned_from
        a_until = a.assigned_until
        # Normalize tz
        from datetime import timezone as tz_module
        if trip_started.tzinfo is None:
            a_from = a_from.replace(tzinfo=None) if a_from.tzinfo else a_from
            a_until = a_until.replace(tzinfo=None) if (a_until and a_until.tzinfo) else a_until
        else:
            if a_from.tzinfo is None:
                a_from = a_from.replace(tzinfo=tz_module.utc)
            if a_until and a_until.tzinfo is None:
                a_until = a_until.replace(tzinfo=tz_module.utc)
        if trip_started >= a_from and (a_until is None or trip_started <= a_until):
            authorized = True
            break

    if not authorized:
        raise HTTPException(status_code=404, detail="Trip not found.")

    kolkata_tz = pytz.timezone("Asia/Kolkata")
    started = trip.started_at
    ended = trip.ended_at
    started_local = started.astimezone(kolkata_tz) if (started and started.tzinfo) else started
    date_str = started_local.strftime("%Y-%m-%d") if started_local else "Unknown"
    duration_seconds: Optional[int] = None
    if started and ended:
        delta = ended - started
        duration_seconds = int(delta.total_seconds())

    return APIResponse(success=True, data=StudentTripItem(
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


# ─── S9 Student Safety Awareness ──────────────────────────────────────────────

class StudentSafetyEventResponse(BaseModel):
    id: int
    type: str
    status: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    latitude: Optional[float] = None
    longitude: Optional[float] = None

@router.get("/me/safety/active", response_model=APIResponse[Optional[StudentSafetyEventResponse]])
async def get_active_safety_event(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(require_student),
):
    """
    Returns the active safety event for the student's currently assigned bus.
    If there is no active event, returns success=True with data=None.
    """
    stmt_user = select(User).where(User.firebase_uid == current_user.firebase_uid)
    db_user = (await db.execute(stmt_user)).scalars().first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Student not found.")

    from app.services.scheduler_service import get_kolkata_now
    now = get_kolkata_now()

    # Get active assignment
    stmt_assign = (
        select(StudentBusAssignment)
        .where(
            StudentBusAssignment.student_id == db_user.id,
            StudentBusAssignment.status == StudentAssignmentStatus.ACTIVE,
            StudentBusAssignment.assigned_from <= now,
            or_(
                StudentBusAssignment.assigned_until.is_(None),
                StudentBusAssignment.assigned_until >= now
            )
        )
    )
    res_assign = await db.execute(stmt_assign)
    assignment = res_assign.scalars().first()

    if not assignment:
        return APIResponse(success=True, data=None)

    from app.models.emergency import Emergency, EmergencyStatus
    # Only POTENTIAL, ACTIVE, ESCALATED, ACKNOWLEDGED are considered active for the student UI.
    active_statuses = [
        EmergencyStatus.POTENTIAL,
        EmergencyStatus.ACTIVE,
        EmergencyStatus.ESCALATED,
        EmergencyStatus.ACKNOWLEDGED
    ]

    stmt_emergency = (
        select(Emergency)
        .where(
            Emergency.bus_id == assignment.bus_id,
            Emergency.status.in_(active_statuses)
        )
        .order_by(Emergency.created_at.desc())
    )
    res_emergency = await db.execute(stmt_emergency)
    emergency = res_emergency.scalars().first()

    if not emergency:
        return APIResponse(success=True, data=None)

    return APIResponse(success=True, data=StudentSafetyEventResponse(
        id=emergency.id,
        type=emergency.type.value,
        status=emergency.status.value,
        description=emergency.description,
        created_at=emergency.created_at,
        updated_at=emergency.updated_at,
        latitude=emergency.latitude,
        longitude=emergency.longitude
    ))

from app.models.parent_registration_request import ParentRegistrationRequest, ParentRequestStatus

@router.get("/me/parent-requests", response_model=APIResponse)
async def get_my_parent_requests(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_student)
):
    """Student views pending parent requests associated with their email."""
    stmt = (
        select(ParentRegistrationRequest)
        .where(
            ParentRegistrationRequest.student_email == current_user.email,
            ParentRegistrationRequest.status == ParentRequestStatus.PENDING
        )
        .order_by(ParentRegistrationRequest.created_at.desc())
    )
    res = await db.execute(stmt)
    requests = res.scalars().all()
    
    # Filter out expired ones dynamically or let the UI know
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    data = []
    for r in requests:
        # Check if expired
        r_expires = r.expires_at.replace(tzinfo=None)
        if r_expires < now:
            continue
            
        data.append({
            "id": r.id,
            "relationship_type": r.relationship_type.value if r.relationship_type else None,
            "status": r.status.value if r.status else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "expires_at": r.expires_at.isoformat() if r.expires_at else None
        })
        
    return APIResponse(success=True, data={"requests": data})

@router.post("/me/parent-requests/{request_id}/accept", response_model=APIResponse)
async def accept_parent_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_student)
):
    stmt = select(ParentRegistrationRequest).where(
        ParentRegistrationRequest.id == request_id,
        ParentRegistrationRequest.student_email == current_user.email
    )
    res = await db.execute(stmt)
    req = res.scalars().first()
    
    if not req:
        raise HTTPException(status_code=404, detail="Request not found.")
        
    if req.status != ParentRequestStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Request is already {req.status.value}.")
        
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    r_expires = req.expires_at.replace(tzinfo=None)
    
    if r_expires < now:
        req.status = ParentRequestStatus.EXPIRED
        await db.commit()
        raise HTTPException(status_code=400, detail="Request has expired.")
        
    req.status = ParentRequestStatus.APPROVED
    req.used_at = now
    await db.commit()
    
    return APIResponse(success=True, data={"message": "Parent request accepted. The parent can now register."})

@router.post("/me/parent-requests/{request_id}/reject", response_model=APIResponse)
async def reject_parent_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_student)
):
    stmt = select(ParentRegistrationRequest).where(
        ParentRegistrationRequest.id == request_id,
        ParentRegistrationRequest.student_email == current_user.email
    )
    res = await db.execute(stmt)
    req = res.scalars().first()
    
    if not req:
        raise HTTPException(status_code=404, detail="Request not found.")
        
    if req.status != ParentRequestStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Request is already {req.status.value}.")
        
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    req.status = ParentRequestStatus.REJECTED
    req.used_at = now
    await db.commit()
    
    return APIResponse(success=True, data={"message": "Parent request rejected."})
