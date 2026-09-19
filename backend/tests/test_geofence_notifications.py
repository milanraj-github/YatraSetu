import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
import pytest
from firebase_admin import messaging
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import Settings, settings
from app.db.database import async_session_factory
from app.models.boarding_point import BoardingPoint
from app.models.bus import Bus
from app.models.device_token import UserDeviceToken
from app.models.enums import (
    DevicePlatform,
    NotificationStatus,
    NotificationType,
    ParentLinkStatus,
    TripStatus,
    UserRole,
)
from app.models.notification import Notification
from app.models.parent_child import ParentChildren, ParentLinkRequest
from app.models.route import Route
from app.models.route_stop import RouteStop
from app.models.trip import Trip
from app.models.user import User
from app.schemas.gps import GPSBatchSyncRequest, GPSPointSyncItem, LocationPingCreate
from app.services import (
    geofence_notification_service,
    gps_service,
    notification_service,
)


# --- TEST SEED HELPERS ---

async def seed_geofence_test_environment(
    bp_lat: float = 13.0000,
    bp_lng: float = 75.0000,
    trip_status: TripStatus = TripStatus.IN_PROGRESS,
):
    """Seed complete test fixture: Bus, Route, BoardingPoint, RouteStop, Driver, Student, Parent, Token, Trip."""
    unique_id = uuid.uuid4().hex[:8]
    async with async_session_factory() as session:
        # 1. Bus
        bus = Bus(
            bus_number=f"BUS-GF-{unique_id.upper()}",
            registration_number=f"KA-20-GF-{unique_id.upper()}",
            capacity=40,
            is_active=True,
        )
        session.add(bus)
        await session.flush()

        # 2. Driver assigned to Bus
        driver = User(
            firebase_uid=f"fb-driver-{unique_id}",
            email=f"driver_{unique_id}@example.com",
            full_name=f"Driver {unique_id}",
            role=UserRole.DRIVER,
            assigned_bus_id=bus.id,
        )
        session.add(driver)

        # 3. Student assigned to Bus
        student = User(
            firebase_uid=f"fb-student-{unique_id}",
            email=f"student_{unique_id}@sode-edu.in",
            full_name=f"Student {unique_id}",
            role=UserRole.STUDENT,
            assigned_bus_id=bus.id,
        )
        session.add(student)

        # 4. Parent
        parent = User(
            firebase_uid=f"fb-parent-{unique_id}",
            email=f"parent_{unique_id}@example.com",
            full_name=f"Parent {unique_id}",
            role=UserRole.PARENT,
        )
        session.add(parent)
        await session.flush()

        # 5. Approved Parent-Child Link
        parent_child = ParentChildren(
            parent_id=parent.id,
            student_id=student.id,
        )
        session.add(parent_child)

        # 6. Device Token for Parent
        token = UserDeviceToken(
            user_id=parent.id,
            fcm_token=f"fcm-token-parent-{unique_id}",
            platform=DevicePlatform.ANDROID,
            is_active=True,
        )
        session.add(token)

        # 7. Route & Boarding Point & RouteStop
        route = Route(
            name=f"Route {unique_id}",
            code=f"R-GF-{unique_id.upper()}",
            is_active=True,
        )
        session.add(route)
        await session.flush()

        bp = BoardingPoint(
            name=f"Campus Main Gate {unique_id}",
            latitude=bp_lat,
            longitude=bp_lng,
            is_active=True,
        )
        session.add(bp)
        await session.flush()

        route_stop = RouteStop(
            route_id=route.id,
            boarding_point_id=bp.id,
            stop_order=1,
        )
        session.add(route_stop)

        # 8. Trip
        trip = Trip(
            route_id=route.id,
            bus_id=bus.id,
            driver_id=driver.id,
            status=trip_status,
            actual_start_at=datetime.now(timezone.utc) if trip_status == TripStatus.IN_PROGRESS else None,
        )
        session.add(trip)
        await session.commit()

        # Refresh all
        await session.refresh(bus)
        await session.refresh(driver)
        await session.refresh(student)
        await session.refresh(parent)
        await session.refresh(token)
        await session.refresh(route)
        await session.refresh(bp)
        await session.refresh(route_stop)
        await session.refresh(trip)

        return {
            "bus": bus,
            "driver": driver,
            "student": student,
            "parent": parent,
            "token": token,
            "route": route,
            "boarding_point": bp,
            "route_stop": route_stop,
            "trip": trip,
        }


def mock_auth(uid: str, email: str):
    return patch(
        "app.core.security.verify_firebase_token",
        return_value={"uid": uid, "email": email},
    )


# ==============================================================================
# A. RADIUS LOGIC TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_radius_outside_nearby_no_notification():
    """GPS point outside the 500m nearby radius produces no notifications."""
    env = await seed_geofence_test_environment(bp_lat=13.0000, bp_lng=75.0000)
    # ~880m away from 13.0000
    lat_far = 13.0080
    lng_far = 75.0000
    now = datetime.now(timezone.utc)

    with patch("firebase_admin.messaging.send", return_value="msg-1"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        async with async_session_factory() as session:
            notifs = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=lat_far,
                longitude=lng_far,
                recorded_at=now,
            )
    assert len(notifs) == 0


@pytest.mark.asyncio
async def test_radius_inside_nearby_triggers_nearby():
    """GPS point ~300m away (inside nearby, outside arrival) generates BUS_NEARBY."""
    env = await seed_geofence_test_environment(bp_lat=13.0000, bp_lng=75.0000)
    # ~300m away from 13.0000
    lat_nearby = 13.0027
    lng_nearby = 75.0000
    now = datetime.now(timezone.utc)

    with patch("firebase_admin.messaging.send", return_value="msg-nearby"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        async with async_session_factory() as session:
            notifs = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=lat_nearby,
                longitude=lng_nearby,
                recorded_at=now,
            )
    assert len(notifs) == 1
    assert notifs[0].notification_type == NotificationType.BUS_NEARBY
    assert notifs[0].recipient_id == env["parent"].id
    assert notifs[0].status == NotificationStatus.SENT


@pytest.mark.asyncio
async def test_radius_inside_arrival_triggers_arrived():
    """GPS point ~50m away (inside arrival radius <= 100m) generates BUS_ARRIVED."""
    env = await seed_geofence_test_environment(bp_lat=13.0000, bp_lng=75.0000)
    # ~55m away from 13.0000
    lat_arrived = 13.0005
    lng_arrived = 75.0000
    now = datetime.now(timezone.utc)

    with patch("firebase_admin.messaging.send", return_value="msg-arrived"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        async with async_session_factory() as session:
            notifs = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=lat_arrived,
                longitude=lng_arrived,
                recorded_at=now,
            )
    assert len(notifs) == 1
    assert notifs[0].notification_type == NotificationType.BUS_ARRIVED
    assert notifs[0].recipient_id == env["parent"].id


@pytest.mark.asyncio
async def test_radius_inside_arrival_does_not_trigger_nearby():
    """GPS point inside arrival radius must NOT generate a BUS_NEARBY notification."""
    env = await seed_geofence_test_environment(bp_lat=13.0000, bp_lng=75.0000)
    lat_arrived = 13.0004
    lng_arrived = 75.0000
    now = datetime.now(timezone.utc)

    with patch("firebase_admin.messaging.send", return_value="msg-1"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        async with async_session_factory() as session:
            notifs = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=lat_arrived,
                longitude=lng_arrived,
                recorded_at=now,
            )
    # Must only contain BUS_ARRIVED, never BUS_NEARBY
    assert len(notifs) == 1
    assert notifs[0].notification_type == NotificationType.BUS_ARRIVED
    assert notifs[0].notification_type != NotificationType.BUS_NEARBY


# ==============================================================================
# B. RECIPIENT LOGIC TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_recipient_approved_parent_receives_notification():
    """Only approved parents (ParentChildren) receive geofence notifications."""
    env = await seed_geofence_test_environment()
    with patch("firebase_admin.messaging.send", return_value="msg-ok"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        async with async_session_factory() as session:
            notifs = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=13.0005,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )
    assert len(notifs) == 1
    assert notifs[0].recipient_id == env["parent"].id


@pytest.mark.asyncio
async def test_recipient_pending_parent_does_not_receive():
    """Pending parent link request does NOT receive geofence notifications."""
    env = await seed_geofence_test_environment()
    # Delete approved ParentChildren and replace with PENDING ParentLinkRequest
    async with async_session_factory() as session:
        await session.execute(
            select(ParentChildren).where(ParentChildren.parent_id == env["parent"].id)
        )
        for pc in (await session.execute(select(ParentChildren))).scalars():
            await session.delete(pc)
        req = ParentLinkRequest(
            parent_id=env["parent"].id,
            student_id=env["student"].id,
            status=ParentLinkStatus.PENDING,
        )
        session.add(req)
        await session.commit()

    with patch("firebase_admin.messaging.send", return_value="msg-ok"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        async with async_session_factory() as session:
            notifs = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=13.0005,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )
    assert len(notifs) == 0


@pytest.mark.asyncio
async def test_recipient_rejected_parent_does_not_receive():
    """Rejected parent link request does NOT receive geofence notifications."""
    env = await seed_geofence_test_environment()
    async with async_session_factory() as session:
        for pc in (await session.execute(select(ParentChildren))).scalars():
            await session.delete(pc)
        req = ParentLinkRequest(
            parent_id=env["parent"].id,
            student_id=env["student"].id,
            status=ParentLinkStatus.REJECTED,
        )
        session.add(req)
        await session.commit()

    with patch("firebase_admin.messaging.send", return_value="msg-ok"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        async with async_session_factory() as session:
            notifs = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=13.0005,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )
    assert len(notifs) == 0


@pytest.mark.asyncio
async def test_recipient_unrelated_parent_does_not_receive():
    """Parent of a student assigned to a DIFFERENT bus does NOT receive notifications."""
    env = await seed_geofence_test_environment()
    # Reassign student to a different bus
    other_bus_id = uuid.uuid4()
    async with async_session_factory() as session:
        other_bus = Bus(
            id=other_bus_id,
            bus_number=f"OTHER-BUS-{uuid.uuid4().hex[:6]}",
            registration_number=f"KA-01-{uuid.uuid4().hex[:4]}",
            capacity=30,
        )
        session.add(other_bus)
        await session.flush()
        st_row = (await session.execute(select(User).where(User.id == env["student"].id))).scalar_one()
        st_row.assigned_bus_id = other_bus.id
        await session.commit()

    with patch("firebase_admin.messaging.send", return_value="msg-ok"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        async with async_session_factory() as session:
            notifs = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=13.0005,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )
    assert len(notifs) == 0


@pytest.mark.asyncio
async def test_recipient_multiple_approved_parents_receive_independently():
    """Multiple approved parents of students on the same bus both receive notifications."""
    env = await seed_geofence_test_environment()
    async with async_session_factory() as session:
        # Create second parent and student
        s2 = User(
            firebase_uid=f"fb-s2-{uuid.uuid4().hex[:6]}",
            email=f"s2_{uuid.uuid4().hex[:6]}@sode-edu.in",
            full_name="Student Two",
            role=UserRole.STUDENT,
            assigned_bus_id=env["bus"].id,
        )
        p2 = User(
            firebase_uid=f"fb-p2-{uuid.uuid4().hex[:6]}",
            email=f"p2_{uuid.uuid4().hex[:6]}@example.com",
            full_name="Parent Two",
            role=UserRole.PARENT,
        )
        session.add_all([s2, p2])
        await session.flush()
        pc2 = ParentChildren(parent_id=p2.id, student_id=s2.id)
        token2 = UserDeviceToken(
            user_id=p2.id,
            fcm_token=f"fcm-tok-p2-{uuid.uuid4().hex}",
            platform=DevicePlatform.IOS,
            is_active=True,
        )
        session.add_all([pc2, token2])
        await session.commit()
        p2_id = p2.id

    with patch("firebase_admin.messaging.send", return_value="msg-ok"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        async with async_session_factory() as session:
            notifs = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=13.0005,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )
    assert len(notifs) == 2
    recipient_ids = {n.recipient_id for n in notifs}
    assert env["parent"].id in recipient_ids
    assert p2_id in recipient_ids


@pytest.mark.asyncio
async def test_recipient_multiple_device_tokens_for_same_parent():
    """Parent with multiple active tokens receives FCM push to all tokens in single notification."""
    env = await seed_geofence_test_environment()
    async with async_session_factory() as session:
        token_ios = UserDeviceToken(
            user_id=env["parent"].id,
            fcm_token=f"fcm-tok-ios-{uuid.uuid4().hex}",
            platform=DevicePlatform.IOS,
            is_active=True,
        )
        session.add(token_ios)
        await session.commit()

    with patch("firebase_admin.messaging.send", return_value="msg-ok") as mock_send, \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        async with async_session_factory() as session:
            notifs = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=13.0005,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )
    assert len(notifs) == 1
    # 1 Notification row created for the parent, but FCM send called for each of their 2 tokens
    assert mock_send.call_count == 2


# ==============================================================================
# C. DEDUPLICATION TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_dedupe_repeated_nearby_gps_suppressed():
    """Subsequent GPS pings in nearby radius within 30 mins do not generate duplicate notifications."""
    env = await seed_geofence_test_environment()
    with patch("firebase_admin.messaging.send", return_value="msg-ok"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        # Ping 1: 300m away
        async with async_session_factory() as session:
            first_notifs = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=13.0027,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )
        assert len(first_notifs) == 1

        # Ping 2: 250m away (still in nearby radius, within 30 min)
        async with async_session_factory() as session:
            second_notifs = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=13.0023,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )
        assert len(second_notifs) == 0


@pytest.mark.asyncio
async def test_dedupe_repeated_arrived_gps_suppressed():
    """Subsequent GPS pings in arrival radius within 30 mins do not generate duplicate notifications."""
    env = await seed_geofence_test_environment()
    with patch("firebase_admin.messaging.send", return_value="msg-ok"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        # Ping 1: 50m away
        async with async_session_factory() as session:
            first = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=13.0005,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )
        assert len(first) == 1

        # Ping 2: 40m away
        async with async_session_factory() as session:
            second = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=13.0004,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )
        assert len(second) == 0


@pytest.mark.asyncio
async def test_dedupe_nearby_and_arrived_have_separate_keys():
    """BUS_NEARBY and BUS_ARRIVED for the same stop have distinct keys and both fire in succession."""
    env = await seed_geofence_test_environment()
    with patch("firebase_admin.messaging.send", return_value="msg-ok"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        # 1. Bus approaches (~300m away) -> BUS_NEARBY
        async with async_session_factory() as session:
            nearby_notifs = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=13.0027,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )
        assert len(nearby_notifs) == 1
        assert nearby_notifs[0].notification_type == NotificationType.BUS_NEARBY

        # 2. Bus arrives (~50m away) -> BUS_ARRIVED
        async with async_session_factory() as session:
            arrived_notifs = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=13.0005,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )
        assert len(arrived_notifs) == 1
        assert arrived_notifs[0].notification_type == NotificationType.BUS_ARRIVED


@pytest.mark.asyncio
async def test_dedupe_different_stops_have_separate_keys():
    """Nearby event at Stop 1 does not suppress Nearby event at Stop 2."""
    env = await seed_geofence_test_environment(bp_lat=13.0000, bp_lng=75.0000)
    # Add second stop ~2km away
    async with async_session_factory() as session:
        bp2 = BoardingPoint(
            name="Second Stop",
            latitude=13.0200,
            longitude=75.0000,
            is_active=True,
        )
        session.add(bp2)
        await session.flush()
        rs2 = RouteStop(
            route_id=env["route"].id,
            boarding_point_id=bp2.id,
            stop_order=2,
        )
        session.add(rs2)
        await session.commit()

    with patch("firebase_admin.messaging.send", return_value="msg-ok"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        # Near Stop 1
        async with async_session_factory() as session:
            n1 = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=13.0027,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )
        assert len(n1) == 1

        # Near Stop 2
        async with async_session_factory() as session:
            n2 = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=13.0227,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )
        assert len(n2) == 1
        assert n2[0].data_payload["boarding_point_name"] == "Second Stop"


@pytest.mark.asyncio
async def test_dedupe_different_trips_have_separate_keys():
    """Same stop on two different trips generates independent notifications."""
    env1 = await seed_geofence_test_environment()
    # Create second trip on same route/bus
    async with async_session_factory() as session:
        trip2 = Trip(
            route_id=env1["route"].id,
            bus_id=env1["bus"].id,
            driver_id=env1["driver"].id,
            status=TripStatus.IN_PROGRESS,
            actual_start_at=datetime.now(timezone.utc),
        )
        session.add(trip2)
        await session.commit()
        await session.refresh(trip2)

    with patch("firebase_admin.messaging.send", return_value="msg-ok"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        async with async_session_factory() as session:
            n1 = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env1["trip"],
                latitude=13.0027,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )
        assert len(n1) == 1

        async with async_session_factory() as session:
            n2 = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=trip2,
                latitude=13.0027,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )
        assert len(n2) == 1


# ==============================================================================
# D. GPS BEHAVIOR & INTEGRATION TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_gps_stale_point_does_not_notify(async_client: AsyncClient):
    """Stale GPS point older than current live location does not generate notifications."""
    env = await seed_geofence_test_environment()
    t_newer = datetime.now(timezone.utc)
    t_stale = t_newer - timedelta(minutes=5)

    with mock_auth(env["driver"].firebase_uid, env["driver"].email), \
         patch("firebase_admin.messaging.send", return_value="msg-ok"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        # First: send newer point far away
        await async_client.post(
            f"/api/v1/trips/{env['trip'].id}/gps",
            json={"latitude": 13.0100, "longitude": 75.0000, "recorded_at": t_newer.isoformat()},
            headers={"Authorization": "Bearer mock-token"},
        )

        # Second: send stale point that would otherwise be inside nearby radius
        res = await async_client.post(
            f"/api/v1/trips/{env['trip'].id}/gps",
            json={"latitude": 13.0027, "longitude": 75.0000, "recorded_at": t_stale.isoformat()},
            headers={"Authorization": "Bearer mock-token"},
        )
        assert res.status_code == 201

    # Verify no notification created for the stale ping
    async with async_session_factory() as session:
        stmt = select(Notification).where(Notification.recipient_id == env["parent"].id)
        notifs = list((await session.execute(stmt)).scalars().all())
        assert len(notifs) == 0


@pytest.mark.asyncio
async def test_gps_accepted_newer_point_notifies(async_client: AsyncClient):
    """Valid accepted GPS ping via /api/v1/trips/{id}/gps triggers geofence notification."""
    env = await seed_geofence_test_environment()
    now = datetime.now(timezone.utc)

    with mock_auth(env["driver"].firebase_uid, env["driver"].email), \
         patch("firebase_admin.messaging.send", return_value="msg-ok") as mock_send, \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        res = await async_client.post(
            f"/api/v1/trips/{env['trip'].id}/gps",
            json={"latitude": 13.0027, "longitude": 75.0000, "recorded_at": now.isoformat()},
            headers={"Authorization": "Bearer mock-token"},
        )
        assert res.status_code == 201
        assert mock_send.call_count >= 1

    async with async_session_factory() as session:
        stmt = select(Notification).where(Notification.recipient_id == env["parent"].id)
        notifs = list((await session.execute(stmt)).scalars().all())
        assert len(notifs) == 1
        assert notifs[0].notification_type == NotificationType.BUS_NEARBY
        assert notifs[0].status == NotificationStatus.SENT


@pytest.mark.asyncio
async def test_gps_duplicate_offline_sync_does_not_duplicate_notification(async_client: AsyncClient):
    """Retrying the same offline batch with identical client_id does not re-trigger notifications."""
    env = await seed_geofence_test_environment()
    cid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    batch_payload = {
        "points": [
            {
                "client_id": cid,
                "latitude": 13.0005,
                "longitude": 75.0000,
                "recorded_at": now.isoformat(),
            }
        ]
    }

    with mock_auth(env["driver"].firebase_uid, env["driver"].email), \
         patch("firebase_admin.messaging.send", return_value="msg-ok") as mock_send, \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        # First sync
        res1 = await async_client.post(
            f"/api/v1/trips/{env['trip'].id}/gps/sync",
            json=batch_payload,
            headers={"Authorization": "Bearer mock-token"},
        )
        assert res1.status_code == 200
        assert res1.json()["accepted"] == 1
        assert mock_send.call_count == 1

        # Second sync: exact duplicate
        res2 = await async_client.post(
            f"/api/v1/trips/{env['trip'].id}/gps/sync",
            json=batch_payload,
            headers={"Authorization": "Bearer mock-token"},
        )
        assert res2.status_code == 200
        assert res2.json()["duplicates"] == 1
        assert res2.json()["accepted"] == 0
        # No extra FCM send call
        assert mock_send.call_count == 1


@pytest.mark.asyncio
async def test_gps_out_of_order_in_batch_processed_chronologically():
    """Batch containing points out-of-order are sorted chronologically so live pointer advances monotonically."""
    env = await seed_geofence_test_environment()
    t1 = datetime.now(timezone.utc) - timedelta(minutes=2)
    t2 = datetime.now(timezone.utc)

    # Batch has newer point first, older point second
    pt_new = GPSPointSyncItem(
        client_id=uuid.uuid4(),
        latitude=13.0005,
        longitude=75.0000,
        recorded_at=t2,
    )
    pt_old = GPSPointSyncItem(
        client_id=uuid.uuid4(),
        latitude=13.0027,
        longitude=75.0000,
        recorded_at=t1,
    )
    batch_in = GPSBatchSyncRequest(points=[pt_new, pt_old])

    with patch("firebase_admin.messaging.send", return_value="msg-ok"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        async with async_session_factory() as session:
            resp = await gps_service.sync_location_pings_batch(
                db=session,
                trip_id=env["trip"].id,
                current_user=env["driver"],
                batch_in=batch_in,
            )
    assert resp.accepted == 2


# ==============================================================================
# E. TRIP & ROUTE LIFECYCLE TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_trip_scheduled_status_does_not_notify():
    """SCHEDULED trips must not generate geofence notifications."""
    env = await seed_geofence_test_environment(trip_status=TripStatus.SCHEDULED)
    with patch("firebase_admin.messaging.send", return_value="msg-ok"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        async with async_session_factory() as session:
            notifs = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=13.0005,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )
    assert len(notifs) == 0


@pytest.mark.asyncio
async def test_trip_completed_status_does_not_notify():
    """COMPLETED trips must not generate geofence notifications."""
    env = await seed_geofence_test_environment(trip_status=TripStatus.COMPLETED)
    with patch("firebase_admin.messaging.send", return_value="msg-ok"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        async with async_session_factory() as session:
            notifs = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=13.0005,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )
    assert len(notifs) == 0


@pytest.mark.asyncio
async def test_trip_cancelled_status_does_not_notify():
    """CANCELLED trips must not generate geofence notifications."""
    env = await seed_geofence_test_environment(trip_status=TripStatus.CANCELLED)
    with patch("firebase_admin.messaging.send", return_value="msg-ok"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        async with async_session_factory() as session:
            notifs = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=13.0005,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )
    assert len(notifs) == 0


@pytest.mark.asyncio
async def test_route_stop_from_another_route_does_not_notify():
    """BoardingPoint belonging to another route does NOT trigger notifications for current trip."""
    env = await seed_geofence_test_environment()
    # Create another route with a stop right at (13.0500, 75.0000)
    async with async_session_factory() as session:
        other_route = Route(name="Other Route", code=f"R-OTH-{uuid.uuid4().hex[:4]}", is_active=True)
        session.add(other_route)
        await session.flush()
        other_bp = BoardingPoint(name="Other Route Stop", latitude=13.0500, longitude=75.0000, is_active=True)
        session.add(other_bp)
        await session.flush()
        other_rs = RouteStop(route_id=other_route.id, boarding_point_id=other_bp.id, stop_order=1)
        session.add(other_rs)
        await session.commit()

    # Bus is right next to other_bp (13.0500, 75.0000), but trip operates env['route']!
    with patch("firebase_admin.messaging.send", return_value="msg-ok"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        async with async_session_factory() as session:
            notifs = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=13.0500,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )
    assert len(notifs) == 0


# ==============================================================================
# F. NOTIFICATION & FCM INTEGRITY TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_notification_row_persisted_with_correct_fields():
    """Notification row persisted in DB contains required data payload fields."""
    env = await seed_geofence_test_environment()
    with patch("firebase_admin.messaging.send", return_value="msg-ok"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        async with async_session_factory() as session:
            notifs = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=13.0005,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )

    assert len(notifs) == 1
    notif = notifs[0]
    payload = notif.data_payload
    assert payload["trip_id"] == str(env["trip"].id)
    assert payload["route_stop_id"] == str(env["route_stop"].id)
    assert payload["boarding_point_id"] == str(env["boarding_point"].id)
    assert payload["boarding_point_name"] == env["boarding_point"].name
    assert payload["bus_id"] == str(env["bus"].id)
    assert payload["event_type"] == "BUS_ARRIVED"
    assert "distance_meters" in payload


@pytest.mark.asyncio
async def test_notification_fcm_success_marks_sent():
    """Successful FCM send marks status SENT and sets sent_at timestamp."""
    env = await seed_geofence_test_environment()
    with patch("firebase_admin.messaging.send", return_value="msg-success"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        async with async_session_factory() as session:
            notifs = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=13.0005,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )

    assert len(notifs) == 1
    assert notifs[0].status == NotificationStatus.SENT
    assert notifs[0].sent_at is not None
    assert notifs[0].error_message is None


@pytest.mark.asyncio
async def test_notification_fcm_failure_preserves_failed_record():
    """FCM delivery failure preserves the notification record with FAILED status."""
    env = await seed_geofence_test_environment()
    with patch("firebase_admin.messaging.send", side_effect=Exception("FCM service unavailable")), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        async with async_session_factory() as session:
            notifs = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=13.0005,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )

    assert len(notifs) == 1
    assert notifs[0].status == NotificationStatus.FAILED
    assert "FCM delivery failed" in notifs[0].error_message


@pytest.mark.asyncio
async def test_notification_stale_device_token_deactivated():
    """UnregisteredError from FCM deactivates the parent's device token."""
    env = await seed_geofence_test_environment()
    with patch("firebase_admin.messaging.send", side_effect=messaging.UnregisteredError("Not registered")), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        async with async_session_factory() as session:
            await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=13.0005,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )

    async with async_session_factory() as session:
        tok = (await session.execute(select(UserDeviceToken).where(UserDeviceToken.id == env["token"].id))).scalar_one()
        assert tok.is_active is False


@pytest.mark.asyncio
async def test_notification_empty_parent_list_no_crash():
    """When a bus has no assigned students or approved parents, processing completes gracefully with 0 notifications."""
    env = await seed_geofence_test_environment()
    # Delete parent link
    async with async_session_factory() as session:
        for pc in (await session.execute(select(ParentChildren))).scalars():
            await session.delete(pc)
        await session.commit()

    with patch("firebase_admin.messaging.send", return_value="msg-ok"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        async with async_session_factory() as session:
            notifs = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=13.0005,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )
    assert len(notifs) == 0


@pytest.mark.asyncio
async def test_radius_exact_arrival_radius_triggers_arrived():
    """GPS point exactly at arrival radius (100.0m) triggers BUS_ARRIVED."""
    env = await seed_geofence_test_environment()
    with patch("app.services.geofence_service.calculate_distance_meters", return_value=100.0), \
         patch("firebase_admin.messaging.send", return_value="msg-exact-arrived"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        async with async_session_factory() as session:
            notifs = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=13.0010,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )
    assert len(notifs) == 1
    assert notifs[0].notification_type == NotificationType.BUS_ARRIVED


@pytest.mark.asyncio
async def test_radius_exact_nearby_radius_triggers_nearby():
    """GPS point exactly at nearby radius (500.0m) triggers BUS_NEARBY."""
    env = await seed_geofence_test_environment()
    with patch("app.services.geofence_service.calculate_distance_meters", return_value=500.0), \
         patch("firebase_admin.messaging.send", return_value="msg-exact-nearby"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        async with async_session_factory() as session:
            notifs = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=13.0045,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )
    assert len(notifs) == 1
    assert notifs[0].notification_type == NotificationType.BUS_NEARBY


@pytest.mark.asyncio
async def test_dedupe_different_recipients_independently_deduplicated():
    """Deduplication lock for Parent 1 does not suppress notification for Parent 2."""
    env = await seed_geofence_test_environment()
    async with async_session_factory() as session:
        p2 = User(
            firebase_uid=f"fb-p2-dedupe-{uuid.uuid4().hex[:6]}",
            email=f"p2_dedupe_{uuid.uuid4().hex[:6]}@example.com",
            full_name="Parent 2 Dedupe",
            role=UserRole.PARENT,
        )
        session.add(p2)
        await session.flush()
        pc2 = ParentChildren(parent_id=p2.id, student_id=env["student"].id)
        tok2 = UserDeviceToken(
            user_id=p2.id,
            fcm_token=f"fcm-tok-p2-dedupe-{uuid.uuid4().hex}",
            platform=DevicePlatform.ANDROID,
            is_active=True,
        )
        session.add_all([pc2, tok2])
        await session.commit()
        p2_id = p2.id

    with patch("firebase_admin.messaging.send", return_value="msg-ok"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        # Pre-set dedupe lock ONLY for env['parent']
        event_key = f"trip:{env['trip'].id}:stop:{env['route_stop'].id}:arrived"
        await notification_service.check_and_acquire_dedupe_lock(
            recipient_id=env["parent"].id,
            notification_type=NotificationType.BUS_ARRIVED,
            event_key=event_key,
        )

        async with async_session_factory() as session:
            notifs = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=13.0005,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )

    # Parent 1 was locked -> suppressed. Parent 2 was not locked -> received!
    assert len(notifs) == 1
    assert notifs[0].recipient_id == p2_id


@pytest.mark.asyncio
async def test_route_multiple_stops_within_radius_handled_deterministically():
    """If two stops on same route are both within nearby radius, notifications are generated for both."""
    env = await seed_geofence_test_environment(bp_lat=13.0000, bp_lng=75.0000)
    async with async_session_factory() as session:
        bp2 = BoardingPoint(
            name="Adjacent Stop",
            latitude=13.0008,
            longitude=75.0000,
            is_active=True,
        )
        session.add(bp2)
        await session.flush()
        rs2 = RouteStop(
            route_id=env["route"].id,
            boarding_point_id=bp2.id,
            stop_order=2,
        )
        session.add(rs2)
        await session.commit()
        rs2_id = rs2.id

    with patch("firebase_admin.messaging.send", return_value="msg-ok"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        async with async_session_factory() as session:
            notifs = await geofence_notification_service.process_gps_geofence_events(
                db=session,
                trip=env["trip"],
                latitude=13.0004,
                longitude=75.0000,
                recorded_at=datetime.now(timezone.utc),
            )
    assert len(notifs) == 2
    stop_ids = {n.data_payload["route_stop_id"] for n in notifs}
    assert str(env["route_stop"].id) in stop_ids
    assert str(rs2_id) in stop_ids


@pytest.mark.asyncio
async def test_gps_redis_failure_during_gps_does_not_notify():
    """If Redis fails during GPS ingestion, GPS is persisted to DB but no geofence notification is triggered."""
    env = await seed_geofence_test_environment()
    ping_in = LocationPingCreate(
        latitude=13.0005,
        longitude=75.0000,
        recorded_at=datetime.now(timezone.utc),
    )

    with patch("app.services.gps_service.update_trip_live_location", return_value=False), \
         patch("firebase_admin.messaging.send", return_value="msg-ok") as mock_send:
        async with async_session_factory() as session:
            location_ping = await gps_service.ingest_location_ping(
                db=session,
                trip_id=env["trip"].id,
                current_user=env["driver"],
                ping_in=ping_in,
            )
            assert location_ping.id is not None
            # Geofence notification was not called because Redis live update returned False
            assert mock_send.call_count == 0


@pytest.mark.asyncio
async def test_gps_offline_batch_retry_does_not_duplicate_notification(async_client: AsyncClient):
    """Retrying an entire batch of offline points returns 0 accepted, 0 new notifications."""
    env = await seed_geofence_test_environment()
    cids = [str(uuid.uuid4()), str(uuid.uuid4())]
    now = datetime.now(timezone.utc)
    batch_payload = {
        "points": [
            {"client_id": cids[0], "latitude": 13.0027, "longitude": 75.0000, "recorded_at": (now - timedelta(seconds=10)).isoformat()},
            {"client_id": cids[1], "latitude": 13.0005, "longitude": 75.0000, "recorded_at": now.isoformat()},
        ]
    }

    with mock_auth(env["driver"].firebase_uid, env["driver"].email), \
         patch("firebase_admin.messaging.send", return_value="msg-ok") as mock_send, \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        # First submission
        res1 = await async_client.post(
            f"/api/v1/trips/{env['trip'].id}/gps/sync",
            json=batch_payload,
            headers={"Authorization": "Bearer mock-token"},
        )
        assert res1.status_code == 200
        assert res1.json()["accepted"] == 2
        first_calls = mock_send.call_count

        # Second submission (retry)
        res2 = await async_client.post(
            f"/api/v1/trips/{env['trip'].id}/gps/sync",
            json=batch_payload,
            headers={"Authorization": "Bearer mock-token"},
        )
        assert res2.status_code == 200
        assert res2.json()["accepted"] == 0
        assert res2.json()["duplicates"] == 2
        # No additional FCM sends
        assert mock_send.call_count == first_calls


# ==============================================================================
# G. CONFIGURATION VALIDATION TESTS
# ==============================================================================

def test_config_geofence_radii_validation():
    """Config validation rejects non-positive radii or nearby <= arrival."""
    # Positive radii where nearby > arrival succeeds
    s = Settings(BUS_NEARBY_RADIUS_METERS=600.0, BUS_ARRIVAL_RADIUS_METERS=150.0)
    assert s.BUS_NEARBY_RADIUS_METERS == 600.0
    assert s.BUS_ARRIVAL_RADIUS_METERS == 150.0

    # nearby <= arrival fails
    with pytest.raises(ValueError, match="must be strictly greater than"):
        Settings(BUS_NEARBY_RADIUS_METERS=100.0, BUS_ARRIVAL_RADIUS_METERS=100.0)

    with pytest.raises(ValueError, match="must be strictly greater than"):
        Settings(BUS_NEARBY_RADIUS_METERS=80.0, BUS_ARRIVAL_RADIUS_METERS=100.0)

    # non-positive fails
    with pytest.raises(ValueError, match="must be strictly greater than 0"):
        Settings(BUS_NEARBY_RADIUS_METERS=-10.0)

    with pytest.raises(ValueError, match="must be strictly greater than 0"):
        Settings(BUS_ARRIVAL_RADIUS_METERS=0.0)
