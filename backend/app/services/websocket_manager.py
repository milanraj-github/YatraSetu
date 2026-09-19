import asyncio
import json
import logging
from typing import Dict, Optional, Set
from fastapi import WebSocket

from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)


def get_location_channel(trip_id: str) -> str:
    """Return the Redis Pub/Sub channel for a trip's live location."""
    return f"smartbus:trip:{trip_id}:location"


class WebSocketManager:
    """Manages active WebSocket subscriptions and Redis Pub/Sub listeners per trip."""

    def __init__(self):
        self._active_connections: Dict[str, Set[WebSocket]] = {}
        self._pubsub_tasks: Dict[str, asyncio.Task] = {}
        self._lock: Optional[asyncio.Lock] = None

    def _get_lock(self) -> asyncio.Lock:
        """Lazily initialize asyncio.Lock to avoid cross-event-loop binding issues in testing."""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def connect(self, trip_id: str, websocket: WebSocket) -> None:
        """Register a new WebSocket connection for a trip."""
        await websocket.accept()
        async with self._get_lock():
            if trip_id not in self._active_connections:
                self._active_connections[trip_id] = set()
            self._active_connections[trip_id].add(websocket)

            # Start Pub/Sub listener task if this is the first connection for the trip
            if trip_id not in self._pubsub_tasks or self._pubsub_tasks[trip_id].done():
                self._pubsub_tasks[trip_id] = asyncio.create_task(
                    self._listen_to_trip_channel(trip_id)
                )

    async def disconnect(self, trip_id: str, websocket: WebSocket) -> None:
        """Unregister a WebSocket connection and clean up Pub/Sub task if empty."""
        async with self._get_lock():
            if trip_id in self._active_connections:
                self._active_connections[trip_id].discard(websocket)
                if not self._active_connections[trip_id]:
                    del self._active_connections[trip_id]
                    if trip_id in self._pubsub_tasks:
                        task = self._pubsub_tasks.pop(trip_id)
                        task.cancel()

    async def broadcast_to_trip(self, trip_id: str, message: dict) -> None:
        """Send a message directly to all active WebSocket connections for a trip."""
        connections = self._active_connections.get(trip_id, set()).copy()
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception as exc:
                logger.debug(f"Failed to send to websocket: {exc}")
                await self.disconnect(trip_id, websocket)

    async def _listen_to_trip_channel(self, trip_id: str) -> None:
        """Background task that listens to Redis Pub/Sub channel and broadcasts to clients."""
        channel_name = get_location_channel(trip_id)
        pubsub = None
        try:
            redis_client = get_redis_client()
            if hasattr(redis_client, "pubsub"):
                pubsub = redis_client.pubsub()
                await pubsub.subscribe(channel_name)
                async for msg in pubsub.listen():
                    if msg and msg.get("type") == "message":
                        data_str = msg.get("data")
                        if isinstance(data_str, str):
                            try:
                                payload = json.loads(data_str)
                                await self.broadcast_to_trip(trip_id, payload)
                            except Exception as exc:
                                logger.warning(f"Error parsing pubsub payload: {exc}")
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.warning(f"Pub/Sub listener error for trip {trip_id}: {exc}")
        finally:
            if pubsub is not None:
                try:
                    await pubsub.unsubscribe(channel_name)
                    await pubsub.aclose()
                except Exception:
                    pass


ws_manager = WebSocketManager()
