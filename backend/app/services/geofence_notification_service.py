from datetime import datetime
import logging
from typing import List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.core.config import settings
from app.models.enums import NotificationChannel, NotificationType, TripStatus, UserRole
from app.models.notification import Notification
from app.models.parent_child import ParentChildren
from app.models.route_stop import RouteStop
from app.models.trip import Trip
from app.models.user import User
from app.services import geofence_service, notification_service

logger = logging.getLogger(__name__)


async def get_approved_parent_recipients(
    db: AsyncSession,
    bus_id: uuid.UUID,
) -> List[uuid.UUID]:
    """Retrieve unique IDs of approved parents of students assigned to the given bus."""
    student_alias = aliased(User)
    stmt = (
        select(ParentChildren.parent_id)
        .join(student_alias, ParentChildren.student_id == student_alias.id)
        .where(
            student_alias.role == UserRole.STUDENT,
            student_alias.assigned_bus_id == bus_id,
        )
        .distinct()
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def process_gps_geofence_events(
    db: AsyncSession,
    trip: Trip,
    latitude: float,
    longitude: float,
    recorded_at: datetime,
) -> List[Notification]:
    """Evaluate GPS proximity against the trip's route stops and trigger geofence notifications.

    Only IN_PROGRESS trips generate geofence notifications.
    Stale GPS points or points outside radii do not generate notifications.
    Redis deduplication guarantees no duplicate notifications per parent per event within 30 mins.
    """
    if trip.status != TripStatus.IN_PROGRESS:
        logger.debug(
            f"Trip {trip.id} is {trip.status.value}; skipping geofence notification check"
        )
        return []

    # 1. Fetch ordered RouteStops belonging strictly to this trip's route
    stmt = (
        select(RouteStop)
        .options(selectinload(RouteStop.boarding_point))
        .where(RouteStop.route_id == trip.route_id)
        .order_by(RouteStop.stop_order.asc())
    )
    result = await db.execute(stmt)
    route_stops = list(result.scalars().all())

    if not route_stops:
        return []

    generated_notifications: List[Notification] = []
    parent_ids: Optional[List[uuid.UUID]] = None

    # 2. Evaluate each route stop for proximity
    for route_stop in route_stops:
        bp = route_stop.boarding_point
        if not bp:
            continue

        distance_meters = await geofence_service.calculate_distance_meters(
            lat1=latitude,
            lon1=longitude,
            lat2=bp.latitude,
            lon2=bp.longitude,
            db=db,
        )

        event_type: Optional[NotificationType] = None
        event_suffix: Optional[str] = None
        title: Optional[str] = None
        body: Optional[str] = None

        if distance_meters <= settings.BUS_ARRIVAL_RADIUS_METERS:
            event_type = NotificationType.BUS_ARRIVED
            event_suffix = "arrived"
            title = f"Bus Arrived: {bp.name}"
            body = f"Bus has arrived at {bp.name}."
        elif distance_meters <= settings.BUS_NEARBY_RADIUS_METERS:
            event_type = NotificationType.BUS_NEARBY
            event_suffix = "nearby"
            title = f"Bus Nearby: {bp.name}"
            body = f"Bus is approaching {bp.name} (~{int(distance_meters)}m away)."
        else:
            # Beyond nearby radius - no notification
            continue

        # 3. Retrieve approved parent recipients lazily once per batch of events
        if parent_ids is None:
            parent_ids = await get_approved_parent_recipients(db, trip.bus_id)

        if not parent_ids:
            logger.debug(
                f"No approved parents found for bus {trip.bus_id}; no notifications to dispatch"
            )
            continue

        # 4. Dispatch notification to each approved parent with Redis deduplication
        event_key = f"trip:{trip.id}:stop:{route_stop.id}:{event_suffix}"
        data_payload = {
            "trip_id": str(trip.id),
            "route_stop_id": str(route_stop.id),
            "boarding_point_id": str(bp.id),
            "boarding_point_name": bp.name,
            "bus_id": str(trip.bus_id),
            "event_type": event_type.value,
            "distance_meters": round(distance_meters, 2),
        }

        for parent_id in parent_ids:
            notif = await notification_service.send_notification(
                db=db,
                recipient_id=parent_id,
                title=title,
                body=body,
                notification_type=event_type,
                channel=NotificationChannel.PUSH,
                data_payload=data_payload,
                event_key=event_key,
            )
            if notif:
                generated_notifications.append(notif)

    return generated_notifications
