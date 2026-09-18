import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.core.redis import set_redis_json, get_redis_json
from app.models.user import User, UserRole
from app.models.bus import Bus, BusStatus
from app.models.driver_assignment import DriverBusAssignment, AssignmentStatus
from app.models.route import Route, BoardingPoint, RouteStop, RouteDirection
from app.models.schedule import TripSchedule, TrackingSession, SessionStatus
from app.models.location import LocationPing
from app.schemas.tracking import (
    GpsIngestRequest, DriverTrackingStatusResponse, BusSummarySchema,
    SessionSummarySchema, RouteSummarySchema, RouteStopSummarySchema,
    ScheduleSummarySchema, LocationPointSchema, LiveTripResponse, ActiveBusTrackingItem
)
from app.services.scheduler_service import evaluate_scheduled_sessions_for_db, get_kolkata_now

logger = logging.getLogger("smartbus.tracking_service")

class GPSValidationError(Exception):
    def __init__(self, message: str, code: str = "GPS_VALIDATION_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)

async def get_driver_tracking_status(db: AsyncSession, driver_user: User) -> DriverTrackingStatusResponse:
    # Ensure current schedules are evaluated
    await evaluate_scheduled_sessions_for_db(db)

    # 1. Find active driver assignment
    stmt_assign = select(DriverBusAssignment).options(selectinload(DriverBusAssignment.bus)).where(
        DriverBusAssignment.driver_id == driver_user.id,
        DriverBusAssignment.status == AssignmentStatus.ACTIVE
    )
    res_assign = await db.execute(stmt_assign)
    assignment = res_assign.scalars().first()

    if not assignment:
        return DriverTrackingStatusResponse(tracking_active=False)

    bus = assignment.bus

    # 2. Find tracking session for today
    today_date = get_kolkata_now().date()
    stmt_session = select(TrackingSession).options(
        selectinload(TrackingSession.route).selectinload(Route.stops).selectinload(RouteStop.boarding_point),
        selectinload(TrackingSession.schedule)
    ).where(
        TrackingSession.bus_id == bus.id,
        TrackingSession.driver_id == driver_user.id,
        TrackingSession.session_date == today_date,
        TrackingSession.status == SessionStatus.ACTIVE
    )
    res_session = await db.execute(stmt_session)
    session = res_session.scalars().first()

    if not session:
        return DriverTrackingStatusResponse(
            tracking_active=False,
            bus=BusSummarySchema(
                id=bus.id,
                bus_number=bus.bus_number,
                registration_number=bus.registration_number,
                status=bus.status
            )
        )

    # Filter route stops based on direction
    direction_stops = [
        s for s in session.route.stops if s.direction == session.direction
    ]
    
    # Sort stops based on direction
    if session.direction == RouteDirection.EVENING:
        direction_stops.sort(key=lambda s: s.sequence_order, reverse=True)
    else:
        direction_stops.sort(key=lambda s: s.sequence_order)

    stop_schemas = [
        RouteStopSummarySchema(
            id=s.boarding_point.id,
            name=s.boarding_point.name,
            sequence_order=s.sequence_order,
            latitude=s.boarding_point.latitude,
            longitude=s.boarding_point.longitude
        ) for s in direction_stops
    ]

    route_schema = RouteSummarySchema(
        id=session.route.id,
        name=session.route.name,
        code=session.route.code,
        direction=session.direction,
        stops=stop_schemas
    )

    schedule_schema = ScheduleSummarySchema(
        id=session.schedule.id,
        start_time=session.schedule.start_time.strftime("%H:%M"),
        end_time=session.schedule.end_time.strftime("%H:%M"),
        direction=session.schedule.direction
    )

    session_schema = SessionSummarySchema(
        id=session.id,
        status=session.status,
        direction=session.direction,
        started_at=session.started_at,
        ended_at=session.ended_at
    )

    return DriverTrackingStatusResponse(
        tracking_active=True,
        bus=BusSummarySchema(
            id=bus.id,
            bus_number=bus.bus_number,
            registration_number=bus.registration_number,
            status=bus.status
        ),
        session=session_schema,
        route=route_schema,
        schedule=schedule_schema
    )

async def ingest_gps_ping(
    db: AsyncSession,
    driver_user: User,
    ping_data: GpsIngestRequest
) -> Dict[str, Any]:
    # 1. Resolve driver assignment
    stmt_assign = select(DriverBusAssignment).where(
        DriverBusAssignment.driver_id == driver_user.id,
        DriverBusAssignment.status == AssignmentStatus.ACTIVE
    )
    res_assign = await db.execute(stmt_assign)
    assignment = res_assign.scalars().first()

    if not assignment:
        raise GPSValidationError(
            message="No authorized bus assignment found for this driver.",
            code="NO_AUTHORIZED_BUS"
        )

    bus_id = assignment.bus_id

    # 2. Resolve active tracking session (prefer MORNING active trip for 24/7 testing)
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
        raise GPSValidationError(
            message="No active authorized tracking session found for driver.",
            code="NO_ACTIVE_TRACKING_SESSION"
        )

    # 3. Check duplicate ping in PostgreSQL
    recorded_at_naive = ping_data.recorded_at.replace(tzinfo=None) if ping_data.recorded_at.tzinfo else ping_data.recorded_at
    stmt_dup = select(LocationPing).where(
        LocationPing.trip_id == session.id,
        LocationPing.recorded_at == recorded_at_naive
    )
    res_dup = await db.execute(stmt_dup)
    if res_dup.scalars().first():
        logger.info(f"Ignored duplicate GPS ping for trip {session.id} at {recorded_at_naive}")
        return {"synced": False, "reason": "DUPLICATE_PING", "trip_id": session.id}

    # 4. Insert into PostgreSQL DB History
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    db_ping = LocationPing(
        trip_id=session.id,
        bus_id=bus_id,
        driver_id=driver_user.id,
        latitude=ping_data.latitude,
        longitude=ping_data.longitude,
        speed=ping_data.speed,
        heading=ping_data.heading,
        accuracy=ping_data.accuracy,
        recorded_at=recorded_at_naive,
        server_received_at=now_utc
    )
    db.add(db_ping)
    await db.commit()
    await db.refresh(db_ping)

    # 5. Redis Latest Location Update (Always update to reflect latest live driver ping)
    redis_key = f"bus:{bus_id}:latest_location"
    is_newer = True

    if is_newer:
        redis_payload = {
            "bus_id": bus_id,
            "trip_id": session.id,
            "driver_id": driver_user.id,
            "latitude": ping_data.latitude,
            "longitude": ping_data.longitude,
            "speed": ping_data.speed,
            "heading": ping_data.heading,
            "accuracy": ping_data.accuracy,
            "recorded_at": recorded_at_naive.isoformat(),
            "updated_at": now_utc.isoformat()
        }
        await set_redis_json(redis_key, redis_payload, ttl=86400)

    return {
        "synced": True,
        "trip_id": session.id,
        "bus_id": bus_id,
        "location": {
            "latitude": ping_data.latitude,
            "longitude": ping_data.longitude,
            "speed": ping_data.speed,
            "heading": ping_data.heading,
            "accuracy": ping_data.accuracy,
            "recorded_at": recorded_at_naive.isoformat()
        }
    }

async def get_live_trip_location(db: AsyncSession, trip_id: int) -> LiveTripResponse:
    stmt = select(TrackingSession).options(selectinload(TrackingSession.bus)).where(TrackingSession.id == trip_id)
    res = await db.execute(stmt)
    session = res.scalars().first()

    if not session:
        raise GPSValidationError(message=f"Trip ID {trip_id} not found.", code="TRIP_NOT_FOUND")

    bus = session.bus
    redis_key = f"bus:{bus.id}:latest_location"
    redis_data = await get_redis_json(redis_key)

    if redis_data:
        location_schema = LocationPointSchema(
            latitude=redis_data["latitude"],
            longitude=redis_data["longitude"],
            speed=redis_data["speed"],
            heading=redis_data["heading"],
            accuracy=redis_data["accuracy"],
            recorded_at=datetime.fromisoformat(redis_data["recorded_at"]),
            updated_at=datetime.fromisoformat(redis_data["updated_at"]) if "updated_at" in redis_data else None
        )
        location_status = "LIVE" if session.status == SessionStatus.ACTIVE else "LAST_KNOWN_LOCATION"
    else:
        # Fallback to DB query for latest historical ping
        stmt_ping = select(LocationPing).where(LocationPing.trip_id == trip_id).order_by(LocationPing.recorded_at.desc())
        res_ping = await db.execute(stmt_ping)
        db_ping = res_ping.scalars().first()

        if db_ping:
            location_schema = LocationPointSchema(
                latitude=db_ping.latitude,
                longitude=db_ping.longitude,
                speed=db_ping.speed,
                heading=db_ping.heading,
                accuracy=db_ping.accuracy,
                recorded_at=db_ping.recorded_at,
                updated_at=db_ping.server_received_at
            )
            location_status = "LAST_KNOWN_LOCATION"
        else:
            location_schema = None
            location_status = "GPS_NOT_AVAILABLE"

    return LiveTripResponse(
        trip_id=session.id,
        bus_id=bus.id,
        bus_number=bus.bus_number,
        status=session.status,
        location_status=location_status,
        location=location_schema
    )

async def get_all_active_buses(db: AsyncSession) -> List[ActiveBusTrackingItem]:
    await evaluate_scheduled_sessions_for_db(db)

    stmt = select(TrackingSession).options(
        selectinload(TrackingSession.bus),
        selectinload(TrackingSession.driver)
    ).where(TrackingSession.status == SessionStatus.ACTIVE)
    res = await db.execute(stmt)
    active_sessions = res.scalars().all()

    active_items = []
    seen_bus_ids = set()
    for session in active_sessions:
        bus = session.bus
        driver = session.driver
        if bus.id in seen_bus_ids:
            continue
        seen_bus_ids.add(bus.id)

        redis_key = f"bus:{bus.id}:latest_location"
        redis_data = await get_redis_json(redis_key)

        if redis_data:
            location_schema = LocationPointSchema(
                latitude=redis_data["latitude"],
                longitude=redis_data["longitude"],
                speed=redis_data["speed"],
                heading=redis_data["heading"],
                accuracy=redis_data["accuracy"],
                recorded_at=datetime.fromisoformat(redis_data["recorded_at"]),
                updated_at=datetime.fromisoformat(redis_data["updated_at"]) if "updated_at" in redis_data else None
            )
            location_status = "LIVE"
        else:
            # Fallback DB ping
            stmt_ping = select(LocationPing).where(LocationPing.trip_id == session.id).order_by(LocationPing.recorded_at.desc())
            res_ping = await db.execute(stmt_ping)
            db_ping = res_ping.scalars().first()

            if db_ping:
                location_schema = LocationPointSchema(
                    latitude=db_ping.latitude,
                    longitude=db_ping.longitude,
                    speed=db_ping.speed,
                    heading=db_ping.heading,
                    accuracy=db_ping.accuracy,
                    recorded_at=db_ping.recorded_at,
                    updated_at=db_ping.server_received_at
                )
                location_status = "LAST_KNOWN_LOCATION"
            else:
                location_schema = None
                location_status = "GPS_NOT_AVAILABLE"

        active_items.append(
            ActiveBusTrackingItem(
                trip_id=session.id,
                bus_id=bus.id,
                bus_number=bus.bus_number,
                registration_number=bus.registration_number,
                status=session.status,
                direction=session.direction,
                driver_name=driver.full_name,
                location_status=location_status,
                location=location_schema
            )
        )

    return active_items
