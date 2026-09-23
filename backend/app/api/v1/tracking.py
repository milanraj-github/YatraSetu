from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_driver
from app.schemas.auth import UserResponse, APIResponse
from app.schemas.tracking import (
    GpsIngestRequest, GpsBatchIngestRequest, StopIntelligenceResponse, StopIntelligenceStopSchema, DriverTrackingStatusResponse, LiveTripResponse, ActiveBusTrackingItem,
    StopIntelligenceResponse, StopIntelligenceStopSchema
)
from app.services.tracking_service import (
    get_driver_tracking_status, ingest_gps_ping, ingest_gps_batch, get_live_trip_location, get_all_active_buses, GPSValidationError
)
from app.models.user import User
from app.models.emergency import Emergency, EmergencyType, EmergencyStatus
import datetime as dt
from datetime import timezone


router = APIRouter(tags=["Tracking & Location"])

async def get_db_user_from_auth(db: AsyncSession, auth_user: UserResponse) -> User:
    """
    Resolves the full DB User record from the authenticated Firebase identity.
    Raises HTTP 404 if the user has not been synced to the database yet.
    Clients must call POST /auth/sync-user on first login.
    """
    from sqlalchemy.future import select
    from fastapi import HTTPException, status as http_status

    stmt = select(User).where(User.firebase_uid == auth_user.firebase_uid)
    res = await db.execute(stmt)
    user = res.scalars().first()

    if not user:
        # Fallback: try matching by email (handles legacy seeded accounts)
        stmt_email = select(User).where(User.email == auth_user.email)
        res_email = await db.execute(stmt_email)
        user = res_email.scalars().first()

    if not user:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail={
                "code": "USER_NOT_FOUND_IN_DB",
                "message": "User not found in database. Please call POST /api/v1/auth/sync-user first.",
            }
        )

    return user

@router.get("/driver/tracking/status", response_model=APIResponse[DriverTrackingStatusResponse])
async def get_driver_status(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(require_driver)
):
    """
    Returns active bus assignment, route, schedule, and tracking status for authenticated driver.
    """
    driver_user = await get_db_user_from_auth(db, current_user)
    status_data = await get_driver_tracking_status(db, driver_user)
    return APIResponse(success=True, data=status_data)

@router.post("/gps/ingest", response_model=APIResponse[Dict[str, Any]])
async def ingest_gps(
    ping_data: GpsIngestRequest, GpsBatchIngestRequest, StopIntelligenceResponse, StopIntelligenceStopSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(require_driver)
):
    """
    Ingests live GPS ping from driver app. Validates session, protects against duplicates,
    stores in PostgreSQL location history and updates Redis latest location cache if newer.
    """
    driver_user = await get_db_user_from_auth(db, current_user)
    try:
        res = await ingest_gps_ping(db, driver_user, ping_data)
        return APIResponse(success=True, data=res)
    except GPSValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message}
        )

@router.get("/trips/{trip_id}/live", response_model=APIResponse[LiveTripResponse])
async def get_trip_live(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Returns live tracking status and current location for a specific trip session.
    """
    try:
        res = await get_live_trip_location(db, trip_id)
        return APIResponse(success=True, data=res)
    except GPSValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": e.code, "message": e.message}
        )

@router.get("/tracking/active-buses", response_model=APIResponse[List[ActiveBusTrackingItem]])
async def get_active_buses(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Returns list of all currently active buses with latest locations, driver names, and trip info.
    """
    res = await get_all_active_buses(db)
    return APIResponse(success=True, data=res)


@router.post("/gps/ingest/batch", response_model=APIResponse[Dict[str, Any]])
async def ingest_gps_batch_endpoint(
    batch_data: GpsBatchIngestRequest, StopIntelligenceResponse, StopIntelligenceStopSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(require_driver)
):
    driver_user = await get_db_user_from_auth(db, current_user)
    try:
        res = await ingest_gps_batch(db, driver_user, batch_data)
        return APIResponse(success=True, data=res)
    except GPSValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message}
        )


@router.get("/gps/stop-intelligence", response_model=APIResponse[StopIntelligenceResponse])
async def get_stop_intelligence(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(require_driver)
):
    from app.services.tracking_service import calculate_stop_intelligence, get_redis_json
    driver_user = await get_db_user_from_auth(db, current_user)
    
    # Get active session
    stmt_assign = select(DriverBusAssignment).where(
        DriverBusAssignment.driver_id == driver_user.id,
        DriverBusAssignment.status == AssignmentStatus.ACTIVE
    )
    res_assign = await db.execute(stmt_assign)
    assignment = res_assign.scalars().first()

    if not assignment:
        return APIResponse(success=True, data={"status": "NO_ACTIVE_TRIP"})
        
    bus_id = assignment.bus_id
    today_date = get_kolkata_now().date()
    
    stmt_session = select(TrackingSession).where(
        TrackingSession.bus_id == bus_id,
        TrackingSession.driver_id == driver_user.id,
        TrackingSession.session_date == today_date,
        TrackingSession.status == SessionStatus.ACTIVE
    ).order_by(TrackingSession.id.asc())
    res_session = await db.execute(stmt_session)
    session = res_session.scalars().first()

    if not session:
        return APIResponse(success=True, data={"status": "NO_ACTIVE_TRIP"})

    redis_key = f"bus:{bus_id}:latest_location"
    latest_loc = await get_redis_json(redis_key)
    
    if not latest_loc or "latitude" not in latest_loc:
        return APIResponse(success=True, data={"status": "GPS_UNAVAILABLE"})
        
    intel = await calculate_stop_intelligence(db, session.id, bus_id, latest_loc["latitude"], latest_loc["longitude"])
    intel["deviation_status"] = latest_loc.get("deviation_status", "ON_ROUTE")
    
    # Phase 9: Attach potential accident state
    stmt_em = select(Emergency).where(
        Emergency.trip_id == session.id,
        Emergency.type == EmergencyType.AUTOMATIC_ACCIDENT,
        Emergency.status.in_([EmergencyStatus.POTENTIAL, EmergencyStatus.ESCALATED])
    )
    res_em = await db.execute(stmt_em)
    emergency = res_em.scalars().first()  # Will get first if ordered, but since it's 1 active event it's fine
    
    if emergency:
        now_utc = dt.datetime.now(timezone.utc).replace(tzinfo=None)
        deadline = emergency.created_at + dt.timedelta(seconds=30)
        
        if emergency.status == EmergencyStatus.POTENTIAL and now_utc > deadline:
            emergency.status = EmergencyStatus.ESCALATED
            await db.commit()
            
        intel["accident_alert_id"] = emergency.id
        intel["accident_deadline_at"] = deadline.isoformat() + "Z"
        intel["accident_status"] = emergency.status.value

    # Phase 11: Check active manual SOS
    stmt_sos = select(Emergency).where(
        Emergency.trip_id == session.id,
        Emergency.type == EmergencyType.MANUAL_SOS,
        Emergency.status.in_([EmergencyStatus.ACTIVE, EmergencyStatus.ACKNOWLEDGED])
    ).order_by(Emergency.id.desc())
    res_sos = await db.execute(stmt_sos)
    active_sos = res_sos.scalars().first()
    if active_sos:
        intel["active_sos_id"] = active_sos.id

    return APIResponse(success=True, data=intel)

@router.post("/gps/accident/{alert_id}/safe")
async def confirm_accident_safe(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(require_driver)
):
    driver_user = await get_db_user_from_auth(db, current_user)
    
    stmt = select(Emergency).where(
        Emergency.id == alert_id,
        Emergency.driver_id == driver_user.id
    )
    res = await db.execute(stmt)
    emergency = res.scalars().first()
    
    if not emergency:
        raise HTTPException(status_code=404, detail="Accident event not found or unauthorized.")
        
    if emergency.status != EmergencyStatus.POTENTIAL:
        return APIResponse(success=True, message=f"Event already {emergency.status.value}")
        
    now_utc = dt.datetime.now(timezone.utc).replace(tzinfo=None)
    deadline = emergency.created_at + dt.timedelta(seconds=30)
    
    if now_utc > deadline:
        emergency.status = EmergencyStatus.ESCALATED
        await db.commit()
        return APIResponse(success=False, message="Too late, event escalated.")
        
    emergency.status = EmergencyStatus.DRIVER_CONFIRMED_SAFE
    emergency.resolved_at = now_utc
    emergency.resolved_by = driver_user.id
    await db.commit()
    
    from app.services.notification_service import notify_students
    from app.models.notification import NotificationPriority
    await notify_students(
        db=db,
        bus_id=emergency.bus_id,
        event_type="SAFETY_RESOLVED",
        title="Safety Alert Resolved",
        message="Safety alert resolved. The driver has confirmed they are safe.",
        priority=NotificationPriority.NORMAL,
        related_entity_id=emergency.id
    )
    
    return APIResponse(success=True, message="Confirmed safe.")

from pydantic import BaseModel
class SOSRequest(BaseModel):
    message: str | None = None

@router.post("/gps/emergency/sos")
async def trigger_manual_sos(
    payload: SOSRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(require_driver)
):
    from app.models.emergency import Emergency, EmergencyType, EmergencySeverity, EmergencyStatus
    from app.services.tracking_service import get_redis_json
    driver_user = await get_db_user_from_auth(db, current_user)
    
    # Get active session
    stmt_assign = select(DriverBusAssignment).where(
        DriverBusAssignment.driver_id == driver_user.id,
        DriverBusAssignment.status == AssignmentStatus.ACTIVE
    )
    res_assign = await db.execute(stmt_assign)
    assignment = res_assign.scalars().first()

    if not assignment:
        raise HTTPException(status_code=403, detail="No active bus assignment.")
        
    bus_id = assignment.bus_id
    today_date = get_kolkata_now().date()
    
    stmt_session = select(TrackingSession).where(
        TrackingSession.bus_id == bus_id,
        TrackingSession.driver_id == driver_user.id,
        TrackingSession.session_date == today_date,
        TrackingSession.status == SessionStatus.ACTIVE
    ).order_by(TrackingSession.id.asc())
    res_session = await db.execute(stmt_session)
    session = res_session.scalars().first()

    if not session:
        raise HTTPException(status_code=403, detail="No active trip found. Cannot send SOS.")
        
    # Prevent duplicate SOS
    stmt_exist = select(Emergency).where(
        Emergency.trip_id == session.id,
        Emergency.type == EmergencyType.MANUAL_SOS,
        Emergency.status.in_([EmergencyStatus.ACTIVE, EmergencyStatus.ACKNOWLEDGED])
    )
    res_exist = await db.execute(stmt_exist)
    existing = res_exist.scalars().first()
    if existing:
        return APIResponse(success=True, data={"sos_id": existing.id}, message="SOS already active.")

    # Get latest location
    redis_key = f"bus:{bus_id}:latest_location"
    latest_loc = await get_redis_json(redis_key)
    
    lat = latest_loc.get("latitude") if latest_loc else None
    lon = latest_loc.get("longitude") if latest_loc else None
    acc = latest_loc.get("accuracy") if latest_loc else None
    
    sos_event = Emergency(
        type=EmergencyType.MANUAL_SOS,
        severity=EmergencySeverity.CRITICAL,
        status=EmergencyStatus.ACTIVE,
        bus_id=bus_id,
        driver_id=driver_user.id,
        trip_id=session.id,
        route_id=session.route_id,
        latitude=lat,
        longitude=lon,
        accuracy=acc,
        description=payload.message or "Manual SOS triggered by Driver",
        source="DRIVER_APP"
    )
    db.add(sos_event)
    await db.commit()
    await db.refresh(sos_event)
    
    # Phase 12 Notification
    from app.services.notification_service import notify_admins
    from app.models.notification import NotificationPriority
    await notify_admins(
        db=db,
        event_type="MANUAL_SOS",
        title=f"🚨 Manual SOS — BUS-{bus_id}",
        message=f"Driver {driver_user.full_name} triggered an emergency on Trip {session.id}.",
        priority=NotificationPriority.CRITICAL,
        related_entity_id=sos_event.id,
        send_email=True
    )
    from app.services.notification_service import notify_students
    await notify_students(
        db=db,
        bus_id=bus_id,
        event_type="MANUAL_SOS",
        title="Emergency Alert",
        message="An emergency SOS has been triggered on your assigned bus. Tap to view the latest available bus information.",
        priority=NotificationPriority.CRITICAL,
        related_entity_id=sos_event.id
    )
    
    return APIResponse(success=True, data={"sos_id": sos_event.id}, message="Emergency sent successfully.")
