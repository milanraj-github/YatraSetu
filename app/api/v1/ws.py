import json
import logging
import uuid
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis_client
from app.core.security import get_websocket_user
from app.db.database import get_db
from app.models.enums import TripStatus, UserRole
from app.models.trip import Trip
from app.models.user import User
from app.services.gps_service import get_live_location_key
from app.services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket Telemetry"])


@router.websocket("/trips/{trip_id}")
async def trip_live_location_ws(
    websocket: WebSocket,
    trip_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Realtime WebSocket endpoint streaming live location telemetry for an active trip."""
    # 1. Authenticate user via token header or query parameter
    try:
        current_user: User = await get_websocket_user(websocket, db)
    except Exception as exc:
        logger.warning(f"WebSocket auth failed: {exc}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
        return

    # 2. Retrieve trip and check existence & lifecycle status
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if not trip:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Trip not found")
        return

    if trip.status in (TripStatus.COMPLETED, TripStatus.CANCELLED):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Trip is not active")
        return

    # 3. Check authorization: ADMIN or assigned DRIVER
    if current_user.role == UserRole.DRIVER:
        if trip.driver_id != current_user.id or trip.bus_id != current_user.assigned_bus_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized trip access")
            return
    elif current_user.role != UserRole.ADMIN:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized role")
        return

    # 4. Accept and register connection
    trip_id_str = str(trip_id)
    await ws_manager.connect(trip_id_str, websocket)

    try:
        # 5. Send initial state: existing Redis live location or connection status
        redis_client = get_redis_client()
        key = get_live_location_key(trip_id)
        raw_live = None
        try:
            raw_live = await redis_client.get(key)
        except Exception as exc:
            logger.debug(f"Redis get failed on WS connect: {exc}")

        if raw_live:
            initial_data = json.loads(raw_live)
            await websocket.send_json(initial_data)
        else:
            await websocket.send_json({"type": "connected", "trip_id": trip_id_str})

        # 6. Keep connection active to process incoming client messages or wait for disconnect
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await ws_manager.disconnect(trip_id_str, websocket)
    except Exception as exc:
        logger.debug(f"WebSocket disconnected: {exc}")
        await ws_manager.disconnect(trip_id_str, websocket)
