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

    # 5. Redis Latest Location Update — only overwrite if this ping is newer
    redis_key = f"bus:{bus_id}:latest_location"
    existing = await get_redis_json(redis_key)

    is_newer = True  # default: no existing data
    if existing and existing.get("recorded_at"):
        try:
            existing_recorded_at = datetime.fromisoformat(existing["recorded_at"])
            is_newer = recorded_at_naive > existing_recorded_at
        except (ValueError, TypeError):
            is_newer = True  # malformed value — overwrite

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
            "updated_at": now_utc.isoformat(),
        }
        await set_redis_json(redis_key, redis_payload, ttl=86400)
        logger.debug(f"Redis updated for bus {bus_id} at {recorded_at_naive.isoformat()}")
    else:
        logger.debug(f"Skipping Redis update for bus {bus_id} — ping at {recorded_at_naive.isoformat()} is older than cached {existing['recorded_at']}")

    return {
        "synced": True,
        "trip_id": session.id,
        "bus_id": bus_id,
        "redis_updated": is_newer,
        "location": {
            "latitude": ping_data.latitude,
            "longitude": ping_data.longitude,
            "speed": ping_data.speed,
            "heading": ping_data.heading,
            "accuracy": ping_data.accuracy,
            "recorded_at": recorded_at_naive.isoformat(),
        },
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
        selectinload(TrackingSession.driver),
        selectinload(TrackingSession.route)
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
                route_id=session.route.id if session.route else None,
                route_name=session.route.name if session.route else None,
                location_status=location_status,
                location=location_schema
            )
        )

    return active_items


async def ingest_gps_batch(
    db: AsyncSession,
    driver_user: User,
    batch_data: 'GpsBatchIngestRequest'
) -> Dict[str, Any]:
    from app.schemas.tracking import GpsBatchIngestResponse
    
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
    today_date = get_kolkata_now().date()
    
    accepted = 0
    duplicates = 0
    rejected = 0
    failed_points = []
    synced_points = []
    
    # Track the latest valid ping for Redis update
    latest_ping_data = None
    latest_ping_time = None
    latest_session = None

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    for ping in batch_data.locations:
        recorded_at_str = ping.recorded_at.isoformat()
        if ping.recorded_at.tzinfo is None:
             recorded_at_str += "Z" # ensure clients can match back
             
        # Resolve active tracking session (could be different if crossing midnight, but typically same day)
        ping_date = ping.recorded_at.astimezone(timezone(timedelta(hours=5, minutes=30))).date() if ping.recorded_at.tzinfo else today_date
        
        # In an offline scenario, the driver might have ended the trip, but we still need to ingest points for that completed trip.
        # We find the trip that was active AT THE TIME of the ping, or just any trip for this driver/bus on that date.
        stmt_session = select(TrackingSession).where(
            TrackingSession.bus_id == bus_id,
            TrackingSession.driver_id == driver_user.id,
            TrackingSession.session_date == ping_date
        ).order_by(TrackingSession.id.desc())
        res_session = await db.execute(stmt_session)
        session = res_session.scalars().first()

        if not session:
            rejected += 1
            failed_points.append(recorded_at_str)
            continue

        # Check duplicate
        recorded_at_naive = ping.recorded_at.replace(tzinfo=None) if ping.recorded_at.tzinfo else ping.recorded_at
        stmt_dup = select(LocationPing).where(
            LocationPing.trip_id == session.id,
            LocationPing.recorded_at == recorded_at_naive
        )
        res_dup = await db.execute(stmt_dup)
        if res_dup.scalars().first():
            duplicates += 1
            synced_points.append(recorded_at_str) # Duplicate is considered successfully handled
            continue

        # Insert
        db_ping = LocationPing(
            trip_id=session.id,
            bus_id=bus_id,
            driver_id=driver_user.id,
            latitude=ping.latitude,
            longitude=ping.longitude,
            speed=ping.speed,
            heading=ping.heading,
            accuracy=ping.accuracy,
            recorded_at=recorded_at_naive,
            server_received_at=now_utc
        )
        db.add(db_ping)
        accepted += 1
        synced_points.append(recorded_at_str)
        
        # Track latest for Redis
        if not latest_ping_time or recorded_at_naive > latest_ping_time:
            latest_ping_time = recorded_at_naive
            latest_ping_data = ping
            latest_session = session

    await db.commit()

    # Redis Update
    if latest_ping_data and latest_session and latest_session.status == SessionStatus.ACTIVE:
        redis_key = f"bus:{bus_id}:latest_location"
        existing = await get_redis_json(redis_key)
        
        should_update = True
        if existing and "recorded_at" in existing:
            try:
                existing_time = datetime.fromisoformat(existing["recorded_at"]).replace(tzinfo=None)
                if existing_time >= latest_ping_time:
                    should_update = False
            except ValueError:
                pass
                
        if should_update:
            new_state = {
                "bus_id": bus_id,
                "trip_id": latest_session.id,
                "route_id": latest_session.route_id,
                "driver_id": driver_user.id,
                "latitude": latest_ping_data.latitude,
                "longitude": latest_ping_data.longitude,
                "speed": latest_ping_data.speed,
                "heading": latest_ping_data.heading,
                "accuracy": latest_ping_data.accuracy,
                "recorded_at": latest_ping_time.isoformat() + "Z",
                "server_received_at": now_utc.isoformat() + "Z"
            }
            await set_redis_json(redis_key, new_state)
            
        # Phase 8: Route Deviation Detection
        try:
            import datetime as dt
            from datetime import timezone
            now_utc = dt.datetime.now(timezone.utc).replace(tzinfo=None)
            if (now_utc - recorded_at_naive).total_seconds() < 300:
                deviation_state = await detect_route_deviation(
                    db, session, bus_id, driver_user.id,
                    ping_data.latitude, ping_data.longitude,
                    ping_data.accuracy, recorded_at_naive
                )
                new_state["deviation_status"] = deviation_state
                await set_redis_json(redis_key, new_state)
                
                # Phase 9: Accident Detection
                await detect_potential_accident(
                    db, session, bus_id, driver_user.id,
                    ping_data, recorded_at_naive, f"trip:{session.id}:accident"
                )
        except Exception as e:
            pass  # Do not fail ingestion if deviation detection errors out

            
            # Phase 8: Route Deviation Detection
            try:
                # only check if it's a relatively recent point (not hours old offline queue)
                import datetime as dt
                if (now_utc - latest_ping_time).total_seconds() < 300:
                    deviation_state = await detect_route_deviation(
                        db, latest_session, bus_id, driver_user.id,
                        latest_ping_data.latitude, latest_ping_data.longitude,
                        latest_ping_data.accuracy, latest_ping_time
                    )
                    new_state["deviation_status"] = deviation_state
                    await set_redis_json(redis_key, new_state)
                    
                    # Phase 9: Accident Detection
                    await detect_potential_accident(
                        db, latest_session, bus_id, driver_user.id,
                        latest_ping_data, latest_ping_time, f"trip:{latest_session.id}:accident"
                    )
            except Exception as e:
                pass  # Do not fail ingestion if deviation detection errors out


    return {
        "accepted": accepted,
        "duplicates": duplicates,
        "rejected": rejected,
        "failed_points": failed_points,
        "synced_points": synced_points
    }


import math
from app.models.route import RouteStop, BoardingPoint, RouteDirection

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 +         math.cos(phi1) * math.cos(phi2) *         math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

async def calculate_stop_intelligence(db, session_id: int, bus_id: int, current_lat: float, current_lng: float) -> dict:
    from app.models.schedule import TrackingSession
    from app.models.route import RouteStop, BoardingPoint
    from app.services.tracking_service import get_redis_json, set_redis_json
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    
    # 1. Fetch Session and Route Stops
    stmt = select(TrackingSession).options(
        selectinload(TrackingSession.route).selectinload(Route.stops).selectinload(RouteStop.boarding_point)
    ).where(TrackingSession.id == session_id)
    res = await db.execute(stmt)
    session = res.scalars().first()
    
    if not session or not session.route:
        return {"status": "ROUTE_UNAVAILABLE", "current_stop": None, "next_stop": None}
        
    stops = [s for s in session.route.stops if s.direction == session.direction]
    stops.sort(key=lambda s: s.sequence_order)
    
    if not stops:
        return {"status": "ROUTE_UNAVAILABLE", "current_stop": None, "next_stop": None}

    # 2. Get Last Visited Sequence from Redis
    redis_key = f"trip:{session_id}:progress"
    progress = await get_redis_json(redis_key) or {"visited_seq": 0}
    visited_seq = progress.get("visited_seq", 0)

    # 3. Check distances against geofences
    at_stop = None
    for stop in stops:
        if stop.sequence_order < visited_seq:
            continue
            
        bp = stop.boarding_point
        if not bp or bp.latitude == 0.0 or bp.longitude == 0.0:
            continue # Invalid coordinate, skip calculation
            
        dist = haversine_distance(current_lat, current_lng, bp.latitude, bp.longitude)
        radius = bp.radius_meters if bp.radius_meters else 50
        
        if dist <= radius:
            at_stop = stop
            # If multiple overlapping, pick the highest valid sequence (in case we skipped one and are at the next)
            visited_seq = stop.sequence_order
            
    # Save back progress if updated
    if at_stop and at_stop.sequence_order >= progress.get("visited_seq", 0):
        await set_redis_json(redis_key, {"visited_seq": visited_seq})
        
    # 4. Determine state
    current_stop_data = None
    next_stop_data = None
    status = "BETWEEN_STOPS"
    
    # helper to format stop
    def format_stop(s):
        return {"id": s.id, "name": s.boarding_point.name, "sequence_order": s.sequence_order}
    
    if at_stop:
        status = "AT_STOP"
        current_stop_data = format_stop(at_stop)
        # Find next stop
        next_stops = [s for s in stops if s.sequence_order > visited_seq]
        if next_stops:
            next_stop_data = format_stop(next_stops[0])
        else:
            status = "TRIP_COMPLETED_AT_DESTINATION"
    else:
        if visited_seq == 0:
            status = "BEFORE_START"
            current_stop_data = {"id": 0, "name": "Not reached", "sequence_order": 0}
            next_stop_data = format_stop(stops[0])
        else:
            # We are between stops
            status = "BETWEEN_STOPS"
            # Current is the last visited
            last_visited = next((s for s in reversed(stops) if s.sequence_order <= visited_seq), None)
            if last_visited:
                current_stop_data = format_stop(last_visited)
            
            # Next is the one after visited
            next_stops = [s for s in stops if s.sequence_order > visited_seq]
            if next_stops:
                next_stop_data = format_stop(next_stops[0])
            else:
                status = "TRIP_COMPLETED_AT_DESTINATION"
                current_stop_data = format_stop(stops[-1])
                next_stop_data = None

    return {
        "status": status,
        "current_stop": current_stop_data,
        "next_stop": next_stop_data
    }


from app.models.alert import Alert, AlertType, AlertSeverity, AlertStatus
import json

def point_to_segment_distance(px, py, ax, ay, bx, by):
    # Equirectangular approximation for small distances
    # x = lon * cos(lat), y = lat
    R = 6371000.0
    
    # Convert to radians
    prx, pry = math.radians(px), math.radians(py)
    arx, ary = math.radians(ax), math.radians(ay)
    brx, bry = math.radians(bx), math.radians(by)
    
    avg_lat = (ary + bry) / 2.0
    
    # Project to flat plane (x, y) in meters
    def project(lon, lat):
        return lon * math.cos(avg_lat) * R, lat * R
        
    p_x, p_y = project(prx, pry)
    a_x, a_y = project(arx, ary)
    b_x, b_y = project(brx, bry)
    
    # Vector AB
    ab_x = b_x - a_x
    ab_y = b_y - a_y
    
    # Vector AP
    ap_x = p_x - a_x
    ap_y = p_y - a_y
    
    # Vector BP
    bp_x = p_x - b_x
    bp_y = p_y - b_y
    
    # Dot products
    dot_ap_ab = ap_x * ab_x + ap_y * ab_y
    dot_ab_ab = ab_x * ab_x + ab_y * ab_y
    
    if dot_ab_ab == 0:
        return math.hypot(p_x - a_x, p_y - a_y)
        
    t = dot_ap_ab / dot_ab_ab
    
    if t < 0.0:
        return math.hypot(ap_x, ap_y)
    elif t > 1.0:
        return math.hypot(bp_x, bp_y)
    else:
        proj_x = a_x + t * ab_x
        proj_y = a_y + t * ab_y
        return math.hypot(p_x - proj_x, p_y - proj_y)

def point_to_polyline_distance(lon, lat, polyline):
    if not polyline or len(polyline) < 2:
        return float('inf')
    
    min_dist = float('inf')
    for i in range(len(polyline) - 1):
        p1 = polyline[i]
        p2 = polyline[i+1]
        
        # Ensure format {"lat": float, "lng": float} or similar
        lat1 = p1.get("lat") or p1.get("latitude")
        lon1 = p1.get("lng") or p1.get("longitude")
        lat2 = p2.get("lat") or p2.get("latitude")
        lon2 = p2.get("lng") or p2.get("longitude")
        
        if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
            continue
            
        dist = point_to_segment_distance(lon, lat, lon1, lat1, lon2, lat2)
        if dist < min_dist:
            min_dist = dist
            
    return min_dist

async def detect_route_deviation(db, session, bus_id, driver_id, current_lat, current_lng, accuracy, timestamp):
    # Thresholds
    ROUTE_DEVIATION_THRESHOLD_METERS = 50.0
    REQUIRED_STRIKES = 3
    
    if not session or not session.route:
        return "ROUTE_UNAVAILABLE"
        
    route_geometry = session.route.route_geometry
    if not route_geometry:
        # Architecture ready, but no geometry configured yet
        return "ON_ROUTE"
        
    # Calculate distance
    dist = point_to_polyline_distance(current_lng, current_lat, route_geometry)
    
    # Allowed corridor = base threshold + accuracy padding
    allowed_corridor = ROUTE_DEVIATION_THRESHOLD_METERS + (accuracy if accuracy else 0.0)
    
    redis_key = f"trip:{session.id}:deviation"
    state_data = await get_redis_json(redis_key) or {"strikes": 0, "state": "ON_ROUTE", "alert_id": None}
    
    strikes = state_data.get("strikes", 0)
    current_state = state_data.get("state", "ON_ROUTE")
    alert_id = state_data.get("alert_id")
    
    if dist > allowed_corridor:
        strikes += 1
        if strikes >= REQUIRED_STRIKES:
            current_state = "DEVIATED"
            # Create Alert if not exists
            if not alert_id:
                alert = Alert(
                    type=AlertType.ROUTE_DEVIATION,
                    severity=AlertSeverity.WARNING,
                    status=AlertStatus.ACTIVE,
                    bus_id=bus_id,
                    driver_id=driver_id,
                    route_id=session.route.id,
                    trip_id=session.id,
                    description=f"Bus deviated {int(dist)}m from the planned route corridor.",
                    source="SYSTEM"
                )
                db.add(alert)
                await db.flush()
                alert_id = alert.id
        else:
            if current_state != "DEVIATED":
                current_state = "POTENTIAL_DEVIATION"
    else:
        strikes = 0
        if current_state == "DEVIATED" and alert_id:
            # Resolve Alert
            from sqlalchemy import update
            from datetime import datetime, timezone
            stmt = update(Alert).where(Alert.id == alert_id).values(
                status=AlertStatus.RESOLVED,
                resolved_at=datetime.now(timezone.utc).replace(tzinfo=None),
                description=Alert.description + f"\nResolved: Bus returned to route."
            )
            await db.execute(stmt)
            alert_id = None
        current_state = "ON_ROUTE"
        
    await set_redis_json(redis_key, {
        "strikes": strikes,
        "state": current_state,
        "alert_id": alert_id
    })
    
    return current_state


from app.models.emergency import Emergency, EmergencyType, EmergencySeverity, EmergencyStatus

async def detect_potential_accident(db, session, bus_id, driver_id, current_ping, current_time, redis_key):
    # Thresholds
    MIN_SPEED_FOR_ACCIDENT = 20.0
    SPEED_DROP_THRESHOLD = 30.0 # Drop of 30 km/h
    POOR_ACCURACY = 100.0
    
    if current_ping.accuracy and current_ping.accuracy > POOR_ACCURACY:
        return None # Ignore poor accuracy
        
    state_data = await get_redis_json(redis_key) or {}
    last_speed = state_data.get("last_speed")
    last_time_str = state_data.get("last_time")
    
    import datetime as dt
    from datetime import timezone
    
    current_speed = current_ping.speed
    
    # Store for next iteration
    await set_redis_json(redis_key, {
        "last_speed": current_speed,
        "last_time": current_time.isoformat() + "Z"
    })
    
    if last_speed is None or last_time_str is None:
        return None
        
    last_time = dt.datetime.fromisoformat(last_time_str.replace("Z", "+00:00")).replace(tzinfo=None)
    time_diff = (current_time - last_time).total_seconds()
    
    if time_diff > 30:
        return None # Too much time passed to correlate deceleration
        
    speed_drop = last_speed - current_speed
    
    # Heuristics:
    # 1. Dropped by SPEED_DROP_THRESHOLD
    # 2. Dropped abruptly to 0 from MIN_SPEED_FOR_ACCIDENT
    
    is_suspicious = False
    trigger_reason = ""
    if speed_drop >= SPEED_DROP_THRESHOLD:
        is_suspicious = True
        trigger_reason = "SUDDEN_SPEED_REDUCTION"
    elif last_speed >= MIN_SPEED_FOR_ACCIDENT and current_speed <= 5.0 and time_diff <= 3.0:
        is_suspicious = True
        trigger_reason = "UNEXPECTED_STOP"
        
    if not is_suspicious:
        return None
        
    # Check if inside a normal stop geofence
    if session and session.route:
        # Check current location against route stops
        from app.models.route import RouteStop, BoardingPoint
        from sqlalchemy.orm import selectinload
        from sqlalchemy import select
        
        # We can just fetch the stops and distance
        stops = [s for s in session.route.stops if s.direction == session.direction]
        for stop in stops:
            bp = stop.boarding_point
            if bp and bp.latitude and bp.longitude:
                dist = haversine_distance(current_ping.latitude, current_ping.longitude, bp.latitude, bp.longitude)
                radius = bp.radius_meters if bp.radius_meters else 50.0
                if dist <= radius:
                    # Near a normal stop, do not trigger
                    return None
                    
    # Prevent duplicate events for the same trip (check if already active potential accident)
    from sqlalchemy import select
    stmt = select(Emergency).where(
        Emergency.trip_id == session.id,
        Emergency.type == EmergencyType.AUTOMATIC_ACCIDENT,
        Emergency.status == EmergencyStatus.POTENTIAL
    )
    res = await db.execute(stmt)
    existing = res.scalars().first()
    
    if existing:
        return existing
        
    # Create Potential Accident Event
    emergency = Emergency(
        type=EmergencyType.AUTOMATIC_ACCIDENT,
        severity=EmergencySeverity.HIGH,
        status=EmergencyStatus.POTENTIAL,
        bus_id=bus_id,
        driver_id=driver_id,
        trip_id=session.id,
        route_id=session.route_id if session else None,
        latitude=current_ping.latitude,
        longitude=current_ping.longitude,
        accuracy=current_ping.accuracy,
        description=f"Potential accident detected. Reason: {trigger_reason}. Speed: {last_speed} -> {current_speed} km/h."
    )
    db.add(emergency)
    await db.flush()
    return emergency


async def evaluate_expired_accidents(db: AsyncSession):
    import datetime as dt
    from datetime import timezone
    from app.models.emergency import Emergency, EmergencyStatus, EmergencyType
    from sqlalchemy import select
    
    now_utc = dt.datetime.now(timezone.utc).replace(tzinfo=None)
    # deadline is created_at + 30 seconds
    # so if created_at < now_utc - 30 seconds, it's expired
    deadline_threshold = now_utc - dt.timedelta(seconds=30)
    
    stmt = select(Emergency).where(
        Emergency.type == EmergencyType.AUTOMATIC_ACCIDENT,
        Emergency.status == EmergencyStatus.POTENTIAL,
        Emergency.created_at <= deadline_threshold
    )
    res = await db.execute(stmt)
    emergencies = res.scalars().all()
    
    from app.services.notification_service import notify_admins
    from app.models.notification import NotificationPriority
    for em in emergencies:
        em.status = EmergencyStatus.ESCALATED
        em.updated_at = now_utc
        # Phase 12 Notification
        await notify_admins(
            db=db,
            event_type="ACCIDENT_ESCALATED",
            title=f"🚨 Accident Alert Escalated",
            message=f"Driver did not confirm safety within 30 seconds for Trip {em.trip_id}.",
            priority=NotificationPriority.CRITICAL,
            related_entity_id=em.id,
            send_email=True
        )
        from app.services.notification_service import notify_students
        await notify_students(
            db=db,
            bus_id=em.bus_id,
            event_type="ACCIDENT_ESCALATED",
            title="Safety Alert",
            message="A safety event has been detected involving your assigned bus. Tap to view details.",
            priority=NotificationPriority.CRITICAL,
            related_entity_id=em.id
        )
    
    if emergencies:
        await db.commit()


async def calculate_eta(db: AsyncSession, session_id: int, current_lat: float, current_lng: float, current_speed_kmh: float, next_stop_data: dict) -> dict:
    from app.models.schedule import TrackingSession
    from app.models.route import RouteStop, Route
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    import math

    if not next_stop_data:
        return {"status": "NO_NEXT_STOP"}
        
    stmt = select(RouteStop).options(selectinload(RouteStop.boarding_point)).where(RouteStop.id == next_stop_data["id"])
    res = await db.execute(stmt)
    stop = res.scalars().first()
    
    if not stop or not stop.boarding_point:
        return {"status": "INSUFFICIENT_DATA"}
        
    stop_lat = stop.boarding_point.latitude
    stop_lng = stop.boarding_point.longitude
    
    # Fallback straight-line distance
    distance_m = haversine_distance(current_lat, current_lng, stop_lat, stop_lng)
    
    # Check for route geometry
    session = await db.get(TrackingSession, session_id)
    approximate = True
    if session:
        route = await db.get(Route, session.route_id)
        if route and route.route_geometry and len(route.route_geometry) > 0:
            # If we had full polyline projection we'd do it here.
            # We'll apply a standard road detour factor.
            distance_m = distance_m * 1.2
            approximate = False
        else:
            distance_m = distance_m * 1.3
            
    if distance_m <= 100:
        return {"status": "ARRIVING", "minutes": 0}
        
    # Speed smoothing: If bus is stopped, assume nominal city speed (15 km/h) to avoid infinite ETA
    speed_kmh = current_speed_kmh if current_speed_kmh > 5 else 15.0
    speed_ms = speed_kmh * (1000.0 / 3600.0)
    
    seconds = distance_m / speed_ms
    minutes = int(seconds // 60)
    
    if minutes == 0:
        return {"status": "ARRIVING", "minutes": 0, "approximate": approximate}
        
    return {"status": "AVAILABLE", "minutes": minutes, "approximate": approximate}
