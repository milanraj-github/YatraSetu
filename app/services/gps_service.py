import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis_client
from app.models.enums import TripStatus, UserRole
from app.models.location import LocationPing
from app.models.trip import Trip
from app.models.user import User
from app.schemas.gps import (
    GPSBatchSyncRequest,
    GPSBatchSyncResponse,
    LiveLocationResponse,
    LocationPingCreate,
)
from app.services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

# Lua script to atomically update live location and publish to channel if new recorded_at >= current recorded_at
LUA_UPDATE_LIVE_LOCATION = """
local key = KEYS[1]
local channel = KEYS[2]
local new_data = ARGV[1]
local new_epoch = tonumber(ARGV[2])

local current = redis.call('GET', key)
if current then
    local current_obj = cjson.decode(current)
    local current_epoch = tonumber(current_obj.recorded_at_epoch or 0)
    if new_epoch >= current_epoch then
        redis.call('SET', key, new_data)
        redis.call('PUBLISH', channel, new_data)
        return 1
    else
        return 0
    end
else
    redis.call('SET', key, new_data)
    redis.call('PUBLISH', channel, new_data)
    return 1
end
"""


def get_live_location_key(trip_id: uuid.UUID) -> str:
    """Return the standard Redis key for a trip's live location."""
    return f"smartbus:trip:{trip_id}:live"


def get_location_channel(trip_id: uuid.UUID) -> str:
    """Return the Redis Pub/Sub channel for a trip's live location."""
    return f"smartbus:trip:{trip_id}:location"


async def update_trip_live_location(
    trip_id: uuid.UUID,
    driver_id: uuid.UUID,
    bus_id: uuid.UUID,
    latitude: float,
    longitude: float,
    recorded_at: datetime,
    received_at: datetime,
    accuracy_meters: Optional[float] = None,
    speed_mps: Optional[float] = None,
    heading_degrees: Optional[float] = None,
) -> bool:
    """Atomically update Redis live location and publish to channel without moving backwards in time."""
    try:
        redis_client = get_redis_client()
        key = get_live_location_key(trip_id)
        channel = get_location_channel(trip_id)

        # Ensure recorded_at has timezone info for epoch calculation
        if recorded_at.tzinfo is None:
            recorded_at = recorded_at.replace(tzinfo=timezone.utc)
        recorded_at_epoch = recorded_at.timestamp()

        payload = {
            "trip_id": str(trip_id),
            "driver_id": str(driver_id),
            "bus_id": str(bus_id),
            "latitude": latitude,
            "longitude": longitude,
            "recorded_at": recorded_at.isoformat(),
            "received_at": received_at.isoformat(),
            "accuracy_meters": accuracy_meters,
            "speed_mps": speed_mps,
            "heading_degrees": heading_degrees,
            "recorded_at_epoch": recorded_at_epoch,
        }
        json_payload = json.dumps(payload)

        result = await redis_client.eval(
            LUA_UPDATE_LIVE_LOCATION,
            2,
            key,
            channel,
            json_payload,
            str(recorded_at_epoch),
        )

        if result == 1:
            # Broadcast to in-process active WebSocket connections
            await ws_manager.broadcast_to_trip(str(trip_id), payload)

        return bool(result == 1)
    except Exception as exc:
        logger.warning(f"Failed to update live location in Redis for trip {trip_id}: {exc}")
        return False


async def cleanup_trip_live_location(trip_id: uuid.UUID) -> None:
    """Remove Redis live location key on trip end or cancellation."""
    try:
        redis_client = get_redis_client()
        key = get_live_location_key(trip_id)
        await redis_client.delete(key)
        # Inform any connected WebSocket subscribers
        await ws_manager.broadcast_to_trip(
            str(trip_id),
            {"type": "trip_ended", "trip_id": str(trip_id)},
        )
    except Exception as exc:
        logger.warning(f"Failed to delete Redis live location for trip {trip_id}: {exc}")


async def ingest_location_ping(
    db: AsyncSession,
    trip_id: uuid.UUID,
    current_user: User,
    ping_in: LocationPingCreate,
) -> LocationPing:
    """Ingest and persist a GPS telemetry ping for an active trip in DB and Redis."""
    # 1. Enforce DRIVER role strictly (Admin cannot ingest GPS on behalf of driver)
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only authenticated drivers can submit GPS location pings",
        )

    # 2. Retrieve trip
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )

    # 3. Enforce Driver Ownership and Assigned Bus verification
    if trip.driver_id != current_user.id or trip.bus_id != current_user.assigned_bus_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: driver is not assigned to operate this trip and bus",
        )

    # 4. Verify Trip Status (Only IN_PROGRESS trips accept GPS)
    if trip.status != TripStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot ingest GPS for trip with status '{trip.status.value}'. Trip must be IN_PROGRESS.",
        )

    # 5. Generate server-controlled received_at timestamp
    server_received_at = datetime.now(timezone.utc)

    location_ping = LocationPing(
        trip_id=trip.id,
        driver_id=current_user.id,
        latitude=ping_in.latitude,
        longitude=ping_in.longitude,
        recorded_at=ping_in.recorded_at,
        received_at=server_received_at,
        accuracy_meters=ping_in.accuracy_meters,
        speed_mps=ping_in.speed_mps,
        heading_degrees=ping_in.heading_degrees,
    )

    db.add(location_ping)
    await db.commit()
    await db.refresh(location_ping)

    # 6. Update Redis live location state and Pub/Sub channel
    await update_trip_live_location(
        trip_id=trip.id,
        driver_id=current_user.id,
        bus_id=trip.bus_id,
        latitude=ping_in.latitude,
        longitude=ping_in.longitude,
        recorded_at=ping_in.recorded_at,
        received_at=server_received_at,
        accuracy_meters=ping_in.accuracy_meters,
        speed_mps=ping_in.speed_mps,
        heading_degrees=ping_in.heading_degrees,
    )

    return location_ping


async def sync_location_pings_batch(
    db: AsyncSession,
    trip_id: uuid.UUID,
    current_user: User,
    batch_in: GPSBatchSyncRequest,
) -> GPSBatchSyncResponse:
    """Ingest a batch of offline-queued GPS points with client_id deduplication."""
    # 1. Enforce DRIVER role strictly
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only authenticated drivers can submit GPS location batches",
        )

    # 2. Retrieve trip
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )

    # 3. Enforce Driver Ownership and Assigned Bus verification
    if trip.driver_id != current_user.id or trip.bus_id != current_user.assigned_bus_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: driver is not assigned to operate this trip and bus",
        )

    # 4. Verify Trip Status (Only IN_PROGRESS trips accept GPS)
    if trip.status != TripStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot sync GPS for trip with status '{trip.status.value}'. Trip must be IN_PROGRESS.",
        )

    # 5. Extract client IDs and check for existing records in DB
    submitted_client_ids = [pt.client_id for pt in batch_in.points]
    existing_records = await db.execute(
        select(LocationPing.client_id).where(
            LocationPing.client_id.in_(submitted_client_ids)
        )
    )
    existing_client_ids = set(existing_records.scalars().all())

    # 6. Deduplicate both against DB and intra-batch duplicates
    server_received_at = datetime.now(timezone.utc)
    seen_batch_ids = set()
    accepted_points = []
    duplicates_count = 0

    for pt in batch_in.points:
        if pt.client_id in existing_client_ids or pt.client_id in seen_batch_ids:
            duplicates_count += 1
        else:
            seen_batch_ids.add(pt.client_id)
            accepted_points.append(pt)

    # 7. Insert accepted pings into DB
    if accepted_points:
        new_pings = [
            LocationPing(
                trip_id=trip.id,
                driver_id=current_user.id,
                client_id=pt.client_id,
                latitude=pt.latitude,
                longitude=pt.longitude,
                recorded_at=pt.recorded_at,
                received_at=server_received_at,
                accuracy_meters=pt.accuracy_meters,
                speed_mps=pt.speed_mps,
                heading_degrees=pt.heading_degrees,
            )
            for pt in accepted_points
        ]
        db.add_all(new_pings)
        await db.commit()

        # 8. Update Redis live location for accepted points
        # To maintain monotonicity, sort chronologically by recorded_at
        sorted_accepted = sorted(accepted_points, key=lambda p: p.recorded_at)
        for pt in sorted_accepted:
            await update_trip_live_location(
                trip_id=trip.id,
                driver_id=current_user.id,
                bus_id=trip.bus_id,
                latitude=pt.latitude,
                longitude=pt.longitude,
                recorded_at=pt.recorded_at,
                received_at=server_received_at,
                accuracy_meters=pt.accuracy_meters,
                speed_mps=pt.speed_mps,
                heading_degrees=pt.heading_degrees,
            )

    return GPSBatchSyncResponse(
        trip_id=trip.id,
        total=len(batch_in.points),
        accepted=len(accepted_points),
        duplicates=duplicates_count,
    )



async def get_trip_location_history(
    db: AsyncSession,
    trip_id: uuid.UUID,
    current_user: User,
) -> Sequence[LocationPing]:
    """Retrieve historical GPS location points for a trip ordered chronologically."""
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )

    if current_user.role == UserRole.DRIVER and trip.driver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Drivers can only view GPS history for their own trips",
        )

    pings_result = await db.execute(
        select(LocationPing)
        .where(LocationPing.trip_id == trip_id)
        .order_by(
            LocationPing.recorded_at.asc(),
            LocationPing.received_at.asc(),
            LocationPing.id.asc(),
        )
    )
    return pings_result.scalars().all()


async def get_trip_live_location(
    db: AsyncSession,
    trip_id: uuid.UUID,
    current_user: User,
) -> LiveLocationResponse:
    """Retrieve current live location for an active trip from Redis."""
    # 1. Retrieve and verify trip exists in PostgreSQL
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )

    # 2. Enforce role-based access
    if current_user.role == UserRole.DRIVER:
        if trip.driver_id != current_user.id or trip.bus_id != current_user.assigned_bus_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: drivers can only view live location for their assigned trips",
            )

    # 3. Query Redis for latest live location state
    try:
        redis_client = get_redis_client()
        key = get_live_location_key(trip_id)
        raw_data = await redis_client.get(key)
    except Exception as exc:
        logger.error(f"Error querying Redis live location for trip {trip_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Live location service temporarily unavailable",
        )

    if not raw_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No live location available for this trip",
        )

    data = json.loads(raw_data)
    return LiveLocationResponse(
        trip_id=uuid.UUID(data["trip_id"]),
        driver_id=uuid.UUID(data["driver_id"]),
        bus_id=uuid.UUID(data["bus_id"]),
        latitude=data["latitude"],
        longitude=data["longitude"],
        recorded_at=datetime.fromisoformat(data["recorded_at"]),
        received_at=datetime.fromisoformat(data["received_at"]),
        accuracy_meters=data.get("accuracy_meters"),
        speed_mps=data.get("speed_mps"),
        heading_degrees=data.get("heading_degrees"),
    )
