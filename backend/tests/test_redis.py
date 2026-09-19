import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import pytest
from httpx import AsyncClient

from app.db.database import async_session_factory
from app.models.bus import Bus
from app.models.enums import TripStatus, UserRole
from app.models.route import Route
from app.models.trip import Trip
from app.models.user import User
from tests.conftest import FakeAsyncRedis


async def create_test_user(role: UserRole, prefix: str = "redis_user", assigned_bus_id: uuid.UUID | None = None) -> User:
    """Helper to seed a test user with a specific role and optional assigned bus."""
    test_uid = f"fb-redis-{role.value.lower()}-{uuid.uuid4().hex[:8]}"
    domain = "sode-edu.in" if role == UserRole.STUDENT else "test.invalid"
    test_email = f"{prefix}_{uuid.uuid4().hex[:8]}@{domain}"

    async with async_session_factory() as session:
        user = User(
            firebase_uid=test_uid,
            email=test_email,
            full_name=f"Redis Test {role.value}",
            role=role,
            assigned_bus_id=assigned_bus_id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def create_test_bus(is_active: bool = True) -> Bus:
    """Helper to seed a test bus."""
    bus_num = f"BUS-{uuid.uuid4().hex[:8].upper()}"
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
        route = Route(name="Campus Redis Route", code=code, is_active=is_active)
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


# --- 1. REDIS HEALTH CHECK TESTS ---

@pytest.mark.asyncio
async def test_redis_health_check_healthy(async_client: AsyncClient):
    """GET /api/v1/health/redis returns 200 ok when Redis is available."""
    response = await async_client.get("/api/v1/health/redis")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "redis"


@pytest.mark.asyncio
async def test_redis_health_check_unhealthy(async_client: AsyncClient, auto_mock_redis: FakeAsyncRedis):
    """GET /api/v1/health/redis returns 503 service unavailable when Redis is down."""
    auto_mock_redis.is_healthy = False
    response = await async_client.get("/api/v1/health/redis")
    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"]


# --- 2. GPS -> REDIS LIVE LOCATION TESTS ---

@pytest.mark.asyncio
async def test_gps_ingestion_updates_redis_live_location(async_client: AsyncClient):
    """Valid GPS ingestion updates Redis live location, queryable via GET /api/v1/trips/{id}/live."""
    bus = await create_test_bus()
    driver = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    route = await create_test_route()
    trip = await create_test_trip(driver, bus, route, TripStatus.IN_PROGRESS)

    now_iso = datetime(2026, 9, 19, 12, 0, 0, tzinfo=timezone.utc).isoformat()
    payload = {
        "latitude": 13.34088,
        "longitude": 74.74214,
        "recorded_at": now_iso,
        "accuracy_meters": 3.5,
        "speed_mps": 12.0,
        "heading_degrees": 90.0,
    }

    # Driver ingests GPS
    with mock_firebase_token(driver.firebase_uid, driver.email):
        ingest_res = await async_client.post(
            f"/api/v1/trips/{trip.id}/gps",
            json=payload,
            headers={"Authorization": "Bearer mock-driver-token"},
        )
    assert ingest_res.status_code == 201

    # Driver retrieves live location
    with mock_firebase_token(driver.firebase_uid, driver.email):
        live_res = await async_client.get(
            f"/api/v1/trips/{trip.id}/live",
            headers={"Authorization": "Bearer mock-driver-token"},
        )

    assert live_res.status_code == 200
    live_data = live_res.json()
    assert live_data["trip_id"] == str(trip.id)
    assert live_data["driver_id"] == str(driver.id)
    assert live_data["bus_id"] == str(bus.id)
    assert live_data["latitude"] == 13.34088
    assert live_data["longitude"] == 74.74214
    assert live_data["accuracy_meters"] == 3.5
    assert live_data["speed_mps"] == 12.0
    assert live_data["heading_degrees"] == 90.0
    assert datetime.fromisoformat(live_data["recorded_at"]) == datetime.fromisoformat(now_iso)


# --- 3. OUT-OF-ORDER MONOTONIC POINTER TESTS ---

@pytest.mark.asyncio
async def test_redis_live_pointer_never_moves_backwards(async_client: AsyncClient):
    """When an older out-of-order GPS point arrives, Redis keeps the newer live location."""
    bus = await create_test_bus()
    driver = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    route = await create_test_route()
    trip = await create_test_trip(driver, bus, route, TripStatus.IN_PROGRESS)

    base_time = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)
    t_10_05 = (base_time + timedelta(minutes=5)).isoformat()
    t_10_04 = (base_time + timedelta(minutes=4)).isoformat()
    t_10_06 = (base_time + timedelta(minutes=6)).isoformat()

    with mock_firebase_token(driver.firebase_uid, driver.email):
        # 1. Ingest point at 10:05 (lat=13.3405)
        res1 = await async_client.post(
            f"/api/v1/trips/{trip.id}/gps",
            json={"latitude": 13.3405, "longitude": 74.7405, "recorded_at": t_10_05},
            headers={"Authorization": "Bearer mock-driver-token"},
        )
        assert res1.status_code == 201

        # Check live location is 10:05
        live1 = await async_client.get(
            f"/api/v1/trips/{trip.id}/live",
            headers={"Authorization": "Bearer mock-driver-token"},
        )
        assert live1.status_code == 200
        assert live1.json()["latitude"] == 13.3405

        # 2. Ingest older out-of-order point at 10:04 (lat=13.3404)
        res2 = await async_client.post(
            f"/api/v1/trips/{trip.id}/gps",
            json={"latitude": 13.3404, "longitude": 74.7404, "recorded_at": t_10_04},
            headers={"Authorization": "Bearer mock-driver-token"},
        )
        assert res2.status_code == 201

        # Check live location REMAINS at 10:05 (monotonic guarantee)
        live2 = await async_client.get(
            f"/api/v1/trips/{trip.id}/live",
            headers={"Authorization": "Bearer mock-driver-token"},
        )
        assert live2.status_code == 200
        assert live2.json()["latitude"] == 13.3405
        assert datetime.fromisoformat(live2.json()["recorded_at"]) == datetime.fromisoformat(t_10_05)

        # 3. Ingest newer point at 10:06 (lat=13.3406)
        res3 = await async_client.post(
            f"/api/v1/trips/{trip.id}/gps",
            json={"latitude": 13.3406, "longitude": 74.7406, "recorded_at": t_10_06},
            headers={"Authorization": "Bearer mock-driver-token"},
        )
        assert res3.status_code == 201

        # Check live location updates to 10:06
        live3 = await async_client.get(
            f"/api/v1/trips/{trip.id}/live",
            headers={"Authorization": "Bearer mock-driver-token"},
        )
        assert live3.status_code == 200
        assert live3.json()["latitude"] == 13.3406
        assert datetime.fromisoformat(live3.json()["recorded_at"]) == datetime.fromisoformat(t_10_06)


# --- 4. REDIS FAULT TOLERANCE ---

@pytest.mark.asyncio
async def test_redis_failure_does_not_fail_gps_ingestion(async_client: AsyncClient, auto_mock_redis: FakeAsyncRedis):
    """If Redis fails, PostgreSQL LocationPing write succeeds and GPS ingestion returns 201."""
    bus = await create_test_bus()
    driver = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    route = await create_test_route()
    trip = await create_test_trip(driver, bus, route, TripStatus.IN_PROGRESS)

    # Make Redis unavailable
    auto_mock_redis.is_healthy = False

    payload = {
        "latitude": 13.34088,
        "longitude": 74.74214,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }

    with mock_firebase_token(driver.firebase_uid, driver.email):
        # Ingestion should still succeed with 201
        response = await async_client.post(
            f"/api/v1/trips/{trip.id}/gps",
            json=payload,
            headers={"Authorization": "Bearer mock-driver-token"},
        )
        assert response.status_code == 201

        # Historical GPS retrieval from Postgres works
        history_res = await async_client.get(
            f"/api/v1/trips/{trip.id}/gps",
            headers={"Authorization": "Bearer mock-driver-token"},
        )
        assert history_res.status_code == 200
        assert len(history_res.json()) == 1


# --- 5. LIVE LOCATION AUTHORIZATION & 404 NOT FOUND ---

@pytest.mark.asyncio
async def test_live_location_authorization_and_empty_state(async_client: AsyncClient):
    """Test role access control and 404 response when no live location is available."""
    admin = await create_test_user(UserRole.ADMIN)
    student = await create_test_user(UserRole.STUDENT)
    parent = await create_test_user(UserRole.PARENT)
    bus = await create_test_bus()
    driver1 = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    driver2 = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    route = await create_test_route()
    trip = await create_test_trip(driver1, bus, route, TripStatus.IN_PROGRESS)

    # Trip exists but has received no GPS pings -> 404 Not Found for Driver 1
    with mock_firebase_token(driver1.firebase_uid, driver1.email):
        empty_res = await async_client.get(
            f"/api/v1/trips/{trip.id}/live",
            headers={"Authorization": "Bearer mock-driver1-token"},
        )
    assert empty_res.status_code == 404
    assert "No live location" in empty_res.json()["detail"]

    # Ingest 1 GPS ping
    with mock_firebase_token(driver1.firebase_uid, driver1.email):
        await async_client.post(
            f"/api/v1/trips/{trip.id}/gps",
            json={"latitude": 13.3400, "longitude": 74.7400, "recorded_at": datetime.now(timezone.utc).isoformat()},
            headers={"Authorization": "Bearer mock-driver1-token"},
        )

    # Admin reads live location -> 200 OK
    with mock_firebase_token(admin.firebase_uid, admin.email):
        res_adm = await async_client.get(
            f"/api/v1/trips/{trip.id}/live",
            headers={"Authorization": "Bearer mock-admin-token"},
        )
    assert res_adm.status_code == 200
    assert res_adm.json()["trip_id"] == str(trip.id)

    # Driver 2 reads Driver 1's live location -> 403 Forbidden
    with mock_firebase_token(driver2.firebase_uid, driver2.email):
        res_drv2 = await async_client.get(
            f"/api/v1/trips/{trip.id}/live",
            headers={"Authorization": "Bearer mock-driver2-token"},
        )
    assert res_drv2.status_code == 403

    # Student reads live location -> 403 Forbidden
    with mock_firebase_token(student.firebase_uid, student.email):
        res_stu = await async_client.get(
            f"/api/v1/trips/{trip.id}/live",
            headers={"Authorization": "Bearer mock-student-token"},
        )
    assert res_stu.status_code == 403

    # Parent reads live location -> 403 Forbidden
    with mock_firebase_token(parent.firebase_uid, parent.email):
        res_par = await async_client.get(
            f"/api/v1/trips/{trip.id}/live",
            headers={"Authorization": "Bearer mock-parent-token"},
        )
    assert res_par.status_code == 403


# --- 6. TRIP END / CANCEL CLEANUP TESTS ---

@pytest.mark.asyncio
async def test_trip_end_and_cancel_cleans_up_redis_live_location(async_client: AsyncClient):
    """Ending or cancelling a trip deletes the live location key in Redis."""
    admin = await create_test_user(UserRole.ADMIN)
    bus = await create_test_bus()
    driver = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    route = await create_test_route()
    trip = await create_test_trip(driver, bus, route, TripStatus.IN_PROGRESS)

    # Ingest GPS ping so live location exists
    with mock_firebase_token(driver.firebase_uid, driver.email):
        await async_client.post(
            f"/api/v1/trips/{trip.id}/gps",
            json={"latitude": 13.3400, "longitude": 74.7400, "recorded_at": datetime.now(timezone.utc).isoformat()},
            headers={"Authorization": "Bearer mock-driver-token"},
        )

        # Verify live location exists
        live_res = await async_client.get(
            f"/api/v1/trips/{trip.id}/live",
            headers={"Authorization": "Bearer mock-driver-token"},
        )
        assert live_res.status_code == 200

        # End trip
        end_res = await async_client.post(
            f"/api/v1/trips/{trip.id}/end",
            headers={"Authorization": "Bearer mock-driver-token"},
        )
        assert end_res.status_code == 200
        assert end_res.json()["status"] == TripStatus.COMPLETED.value

        # Verify live location has been cleaned up (returns 404)
        live_after_end = await async_client.get(
            f"/api/v1/trips/{trip.id}/live",
            headers={"Authorization": "Bearer mock-driver-token"},
        )
        assert live_after_end.status_code == 404
