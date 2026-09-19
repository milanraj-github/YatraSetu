import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import pytest
from httpx import AsyncClient
from starlette.websockets import WebSocketDisconnect

from app.db.database import async_session_factory
from app.main import app
from app.models.bus import Bus
from app.models.enums import TripStatus, UserRole
from app.models.route import Route
from app.models.trip import Trip
from app.models.user import User
from tests.conftest import ASGIWebSocketTestSession


async def create_test_user(role: UserRole, prefix: str = "ws_user", assigned_bus_id: uuid.UUID | None = None) -> User:
    """Helper to seed a test user with a specific role and optional assigned bus."""
    test_uid = f"fb-ws-{role.value.lower()}-{uuid.uuid4().hex[:8]}"
    domain = "sode-edu.in" if role == UserRole.STUDENT else "test.invalid"
    test_email = f"{prefix}_{uuid.uuid4().hex[:8]}@{domain}"

    async with async_session_factory() as session:
        user = User(
            firebase_uid=test_uid,
            email=test_email,
            full_name=f"WS Test {role.value}",
            role=role,
            assigned_bus_id=assigned_bus_id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def create_test_bus(is_active: bool = True) -> Bus:
    """Helper to seed a test bus."""
    bus_num = f"BUS-{uuid.uuid4().hex[:6].upper()}"
    reg_num = f"KA-20-{uuid.uuid4().hex[:8].upper()}"

    async with async_session_factory() as session:
        bus = Bus(
            bus_number=bus_num,
            registration_number=reg_num,
            capacity=40,
            is_active=is_active,
        )
        session.add(bus)
        await session.commit()
        await session.refresh(bus)
        return bus


async def create_test_route(is_active: bool = True) -> Route:
    """Helper to seed a test route."""
    code = f"R-{uuid.uuid4().hex[:6].upper()}"
    async with async_session_factory() as session:
        route = Route(name="Campus WS Route", code=code, is_active=is_active)
        session.add(route)
        await session.commit()
        await session.refresh(route)
        return route


async def create_test_trip(
    driver: User,
    bus: Bus,
    route: Route,
    status: TripStatus = TripStatus.IN_PROGRESS,
) -> Trip:
    """Helper to seed a test trip."""
    async with async_session_factory() as session:
        trip = Trip(
            route_id=route.id,
            bus_id=bus.id,
            driver_id=driver.id,
            status=status,
            actual_start_at=datetime.now(timezone.utc) if status == TripStatus.IN_PROGRESS else None,
        )
        session.add(trip)
        await session.commit()
        await session.refresh(trip)
        return trip


def mock_firebase_token(uid: str, email: str):
    return patch(
        "app.core.security.verify_firebase_token",
        return_value={"uid": uid, "email": email},
    )


# --- 1. AUTHENTICATION & ROLE ACCESS TESTS ---

@pytest.mark.asyncio
async def test_websocket_missing_and_invalid_token():
    """Unauthenticated or invalid token connections must be rejected."""
    fake_trip_id = uuid.uuid4()

    # Missing token -> rejected
    with pytest.raises(WebSocketDisconnect) as exc1:
        async with ASGIWebSocketTestSession(app, f"/api/v1/ws/trips/{fake_trip_id}"):
            pass
    assert exc1.value.code == 1008

    # Invalid token -> rejected
    with pytest.raises(WebSocketDisconnect) as exc2:
        async with ASGIWebSocketTestSession(app, f"/api/v1/ws/trips/{fake_trip_id}", query_params={"token": "invalid-token"}):
            pass
    assert exc2.value.code == 1008


@pytest.mark.asyncio
async def test_websocket_role_authorization():
    """STUDENT, PARENT, and unrelated DRIVER must be rejected from WebSocket subscription."""
    admin = await create_test_user(UserRole.ADMIN)
    student = await create_test_user(UserRole.STUDENT)
    parent = await create_test_user(UserRole.PARENT)
    bus = await create_test_bus()
    driver1 = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    driver2 = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    route = await create_test_route()
    trip = await create_test_trip(driver1, bus, route, TripStatus.IN_PROGRESS)

    # Student -> 1008
    with mock_firebase_token(student.firebase_uid, student.email):
        with pytest.raises(WebSocketDisconnect) as exc:
            async with ASGIWebSocketTestSession(app, f"/api/v1/ws/trips/{trip.id}", query_params={"token": "mock-student-token"}):
                pass
        assert exc.value.code == 1008

    # Parent -> 1008
    with mock_firebase_token(parent.firebase_uid, parent.email):
        with pytest.raises(WebSocketDisconnect) as exc:
            async with ASGIWebSocketTestSession(app, f"/api/v1/ws/trips/{trip.id}", query_params={"token": "mock-parent-token"}):
                pass
        assert exc.value.code == 1008

    # Unrelated driver -> 1008
    with mock_firebase_token(driver2.firebase_uid, driver2.email):
        with pytest.raises(WebSocketDisconnect) as exc:
            async with ASGIWebSocketTestSession(app, f"/api/v1/ws/trips/{trip.id}", query_params={"token": "mock-driver2-token"}):
                pass
        assert exc.value.code == 1008

    # Admin -> Connected
    with mock_firebase_token(admin.firebase_uid, admin.email):
        async with ASGIWebSocketTestSession(app, f"/api/v1/ws/trips/{trip.id}", query_params={"token": "mock-admin-token"}) as ws:
            msg = await ws.receive_json()
            assert msg.get("type") == "connected" or msg.get("trip_id") == str(trip.id)


# --- 2. TRIP LIFECYCLE REJECTION TESTS ---

@pytest.mark.asyncio
async def test_websocket_lifecycle_status_rejection():
    """COMPLETED and CANCELLED trips reject WebSocket subscriptions."""
    bus = await create_test_bus()
    driver = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    route = await create_test_route()
    trip_completed = await create_test_trip(driver, bus, route, TripStatus.COMPLETED)
    trip_cancelled = await create_test_trip(driver, bus, route, TripStatus.CANCELLED)

    with mock_firebase_token(driver.firebase_uid, driver.email):
        # Completed trip -> rejected
        with pytest.raises(WebSocketDisconnect) as exc1:
            async with ASGIWebSocketTestSession(app, f"/api/v1/ws/trips/{trip_completed.id}", query_params={"token": "mock-driver-token"}):
                pass
        assert exc1.value.code == 1008

        # Cancelled trip -> rejected
        with pytest.raises(WebSocketDisconnect) as exc2:
            async with ASGIWebSocketTestSession(app, f"/api/v1/ws/trips/{trip_cancelled.id}", query_params={"token": "mock-driver-token"}):
                pass
        assert exc2.value.code == 1008


# --- 3. INITIAL STATE & REALTIME STREAMING TESTS ---

@pytest.mark.asyncio
async def test_websocket_initial_state_and_realtime_gps_updates(async_client: AsyncClient):
    """Client receives initial live state immediately upon connect, plus live updates on ingestion."""
    bus = await create_test_bus()
    driver = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    route = await create_test_route()
    trip = await create_test_trip(driver, bus, route, TripStatus.IN_PROGRESS)

    # 1. Connect when no GPS exists -> receives {"type": "connected", "trip_id": ...}
    with mock_firebase_token(driver.firebase_uid, driver.email):
        async with ASGIWebSocketTestSession(app, f"/api/v1/ws/trips/{trip.id}", query_params={"token": "mock-driver-token"}) as ws1:
            init_msg = await ws1.receive_json()
            assert init_msg["type"] == "connected"
            assert init_msg["trip_id"] == str(trip.id)

    # 2. Ingest 1st GPS point at 10:05
    base_time = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)
    t_10_05 = (base_time + timedelta(minutes=5)).isoformat()
    t_10_04 = (base_time + timedelta(minutes=4)).isoformat()
    t_10_06 = (base_time + timedelta(minutes=6)).isoformat()

    with mock_firebase_token(driver.firebase_uid, driver.email):
        # Ingest 10:05 point
        res1 = await async_client.post(
            f"/api/v1/trips/{trip.id}/gps",
            json={"latitude": 13.3405, "longitude": 74.7405, "recorded_at": t_10_05},
            headers={"Authorization": "Bearer mock-driver-token"},
        )
        assert res1.status_code == 201

        # Connect new client -> should receive initial live location (10:05) immediately
        async with ASGIWebSocketTestSession(app, f"/api/v1/ws/trips/{trip.id}", query_params={"token": "mock-driver-token"}) as ws2:
            initial_live = await ws2.receive_json()
            assert initial_live["latitude"] == 13.3405
            assert datetime.fromisoformat(initial_live["recorded_at"]) == datetime.fromisoformat(t_10_05)

            # 3. Ingest stale point (10:04) -> should NOT broadcast stale update
            await async_client.post(
                f"/api/v1/trips/{trip.id}/gps",
                json={"latitude": 13.3404, "longitude": 74.7404, "recorded_at": t_10_04},
                headers={"Authorization": "Bearer mock-driver-token"},
            )

            # 4. Ingest newer point (10:06) -> should broadcast 10:06 live update
            await async_client.post(
                f"/api/v1/trips/{trip.id}/gps",
                json={"latitude": 13.3406, "longitude": 74.7406, "recorded_at": t_10_06},
                headers={"Authorization": "Bearer mock-driver-token"},
            )

            # Next message received on WebSocket must be the 10:06 point (not 10:04!)
            update_msg = await ws2.receive_json()
            assert update_msg["latitude"] == 13.3406
            assert datetime.fromisoformat(update_msg["recorded_at"]) == datetime.fromisoformat(t_10_06)


# --- 4. MULTI-CLIENT BROADCAST TEST ---

@pytest.mark.asyncio
async def test_websocket_multi_client_broadcast(async_client: AsyncClient):
    """Multiple connected clients (e.g. Admin and Driver) both receive live updates."""
    admin = await create_test_user(UserRole.ADMIN)
    bus = await create_test_bus()
    driver = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    route = await create_test_route()
    trip = await create_test_trip(driver, bus, route, TripStatus.IN_PROGRESS)

    now_iso = datetime.now(timezone.utc).isoformat()

    with mock_firebase_token(admin.firebase_uid, admin.email):
        async with ASGIWebSocketTestSession(app, f"/api/v1/ws/trips/{trip.id}", query_params={"token": "mock-admin-token"}) as ws_admin:
            await ws_admin.receive_json()  # Consume initial connected message

            with mock_firebase_token(driver.firebase_uid, driver.email):
                async with ASGIWebSocketTestSession(app, f"/api/v1/ws/trips/{trip.id}", query_params={"token": "mock-driver-token"}) as ws_driver:
                    await ws_driver.receive_json()  # Consume initial connected message

                    # Ingest GPS
                    await async_client.post(
                        f"/api/v1/trips/{trip.id}/gps",
                        json={"latitude": 13.3410, "longitude": 74.7410, "recorded_at": now_iso},
                        headers={"Authorization": "Bearer mock-driver-token"},
                    )

                    # Both clients receive the update
                    msg_admin = await ws_admin.receive_json()
                    msg_driver = await ws_driver.receive_json()

                    assert msg_admin["latitude"] == 13.3410
                    assert msg_driver["latitude"] == 13.3410
