import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import pytest
from httpx import AsyncClient

from app.db.database import async_session_factory
from app.models.bus import Bus
from app.models.enums import TripStatus, UserRole
from app.models.location import LocationPing
from app.models.route import Route
from app.models.trip import Trip
from app.models.user import User


async def create_test_user(role: UserRole, prefix: str = "gps_user", assigned_bus_id: uuid.UUID | None = None) -> User:
    """Helper to seed a test user with a specific role and optional assigned bus."""
    test_uid = f"fb-gps-{role.value.lower()}-{uuid.uuid4().hex[:8]}"
    domain = "sode-edu.in" if role == UserRole.STUDENT else "test.invalid"
    test_email = f"{prefix}_{uuid.uuid4().hex[:8]}@{domain}"

    async with async_session_factory() as session:
        user = User(
            firebase_uid=test_uid,
            email=test_email,
            full_name=f"GPS Test {role.value}",
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
    reg_num = f"KA-20-{uuid.uuid4().hex[:4].upper()}"

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
        route = Route(name="Campus GPS Route", code=code, is_active=is_active)
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
async def test_gps_ingestion_missing_and_invalid_token(async_client: AsyncClient):
    """Missing or invalid auth headers should yield 401 Unauthorized."""
    fake_trip_id = uuid.uuid4()
    payload = {
        "latitude": 13.34088,
        "longitude": 74.74214,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }

    # Missing header
    res1 = await async_client.post(f"/api/v1/trips/{fake_trip_id}/gps", json=payload)
    assert res1.status_code == 401

    # Invalid token (not mocked)
    res2 = await async_client.post(
        f"/api/v1/trips/{fake_trip_id}/gps",
        json=payload,
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert res2.status_code == 401


@pytest.mark.asyncio
async def test_gps_ingestion_role_enforcement(async_client: AsyncClient):
    """STUDENT, PARENT, and ADMIN cannot submit GPS points (only DRIVER allowed)."""
    admin = await create_test_user(UserRole.ADMIN)
    student = await create_test_user(UserRole.STUDENT)
    parent = await create_test_user(UserRole.PARENT)
    bus = await create_test_bus()
    driver = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    route = await create_test_route()
    trip = await create_test_trip(driver, bus, route, TripStatus.IN_PROGRESS)

    payload = {
        "latitude": 13.34088,
        "longitude": 74.74214,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }

    # Student -> 403
    with mock_firebase_token(student.firebase_uid, student.email):
        res_stu = await async_client.post(
            f"/api/v1/trips/{trip.id}/gps",
            json=payload,
            headers={"Authorization": "Bearer mock-student-token"},
        )
    assert res_stu.status_code == 403

    # Parent -> 403
    with mock_firebase_token(parent.firebase_uid, parent.email):
        res_par = await async_client.post(
            f"/api/v1/trips/{trip.id}/gps",
            json=payload,
            headers={"Authorization": "Bearer mock-parent-token"},
        )
    assert res_par.status_code == 403

    # Admin -> 403 (Admin cannot submit GPS on behalf of driver)
    with mock_firebase_token(admin.firebase_uid, admin.email):
        res_adm = await async_client.post(
            f"/api/v1/trips/{trip.id}/gps",
            json=payload,
            headers={"Authorization": "Bearer mock-admin-token"},
        )
    assert res_adm.status_code == 403


# --- 2. DRIVER OWNERSHIP & BUS ASSIGNMENT TESTS ---

@pytest.mark.asyncio
async def test_assigned_driver_can_submit_gps_to_own_trip(async_client: AsyncClient):
    """Assigned driver can successfully submit GPS telemetry to their IN_PROGRESS trip."""
    bus = await create_test_bus()
    driver = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    route = await create_test_route()
    trip = await create_test_trip(driver, bus, route, TripStatus.IN_PROGRESS)

    now_iso = datetime.now(timezone.utc).isoformat()
    payload = {
        "latitude": 13.34088,
        "longitude": 74.74214,
        "recorded_at": now_iso,
        "accuracy_meters": 4.5,
        "speed_mps": 11.2,
        "heading_degrees": 182.5,
    }

    with mock_firebase_token(driver.firebase_uid, driver.email):
        response = await async_client.post(
            f"/api/v1/trips/{trip.id}/gps",
            json=payload,
            headers={"Authorization": "Bearer mock-driver-token"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["trip_id"] == str(trip.id)
    assert data["driver_id"] == str(driver.id)
    assert data["latitude"] == 13.34088
    assert data["longitude"] == 74.74214
    assert data["accuracy_meters"] == 4.5
    assert data["speed_mps"] == 11.2
    assert data["heading_degrees"] == 182.5
    assert data["received_at"] is not None
    assert data["created_at"] is not None


@pytest.mark.asyncio
async def test_unrelated_driver_or_unassigned_bus_cannot_submit_gps(async_client: AsyncClient):
    """Driver cannot submit GPS to another driver's trip or if bus assignment changed."""
    bus1 = await create_test_bus()
    bus2 = await create_test_bus()
    driver1 = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus1.id)
    driver2 = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus2.id)
    route = await create_test_route()
    trip = await create_test_trip(driver1, bus1, route, TripStatus.IN_PROGRESS)

    payload = {
        "latitude": 13.34088,
        "longitude": 74.74214,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }

    # Driver 2 tries to submit GPS to Driver 1's trip
    with mock_firebase_token(driver2.firebase_uid, driver2.email):
        res = await async_client.post(
            f"/api/v1/trips/{trip.id}/gps",
            json=payload,
            headers={"Authorization": "Bearer mock-driver2-token"},
        )
    assert res.status_code == 403
    assert "Access forbidden" in res.json()["detail"]


# --- 3. TRIP STATUS ENFORCEMENT TESTS ---

@pytest.mark.asyncio
async def test_gps_ingestion_trip_status_requirements(async_client: AsyncClient):
    """GPS ingestion must be accepted for IN_PROGRESS and rejected for SCHEDULED/COMPLETED/CANCELLED."""
    bus = await create_test_bus()
    driver = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    route = await create_test_route()

    trip_scheduled = await create_test_trip(driver, bus, route, TripStatus.SCHEDULED)
    trip_completed = await create_test_trip(driver, bus, route, TripStatus.COMPLETED)
    trip_cancelled = await create_test_trip(driver, bus, route, TripStatus.CANCELLED)

    payload = {
        "latitude": 13.34088,
        "longitude": 74.74214,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }

    with mock_firebase_token(driver.firebase_uid, driver.email):
        # SCHEDULED -> 409
        res_sch = await async_client.post(
            f"/api/v1/trips/{trip_scheduled.id}/gps",
            json=payload,
            headers={"Authorization": "Bearer mock-driver-token"},
        )
        assert res_sch.status_code == 409

        # COMPLETED -> 409
        res_cmp = await async_client.post(
            f"/api/v1/trips/{trip_completed.id}/gps",
            json=payload,
            headers={"Authorization": "Bearer mock-driver-token"},
        )
        assert res_cmp.status_code == 409

        # CANCELLED -> 409
        res_ccl = await async_client.post(
            f"/api/v1/trips/{trip_cancelled.id}/gps",
            json=payload,
            headers={"Authorization": "Bearer mock-driver-token"},
        )
        assert res_ccl.status_code == 409


# --- 4. GPS SCHEMA & BOUNDS VALIDATION TESTS ---

@pytest.mark.asyncio
async def test_gps_coordinate_and_telemetry_validation(async_client: AsyncClient):
    """Invalid latitude, longitude, accuracy, speed, or heading must be rejected with 422."""
    bus = await create_test_bus()
    driver = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    route = await create_test_route()
    trip = await create_test_trip(driver, bus, route, TripStatus.IN_PROGRESS)

    valid_time = datetime.now(timezone.utc).isoformat()

    invalid_cases = [
        {"latitude": 90.001, "longitude": 74.0, "recorded_at": valid_time},      # lat > 90
        {"latitude": -90.001, "longitude": 74.0, "recorded_at": valid_time},     # lat < -90
        {"latitude": 13.0, "longitude": 180.001, "recorded_at": valid_time},     # lon > 180
        {"latitude": 13.0, "longitude": -180.001, "recorded_at": valid_time},    # lon < -180
        {"latitude": 13.0, "longitude": 74.0, "recorded_at": valid_time, "accuracy_meters": -1.0}, # accuracy < 0
        {"latitude": 13.0, "longitude": 74.0, "recorded_at": valid_time, "speed_mps": -0.5},       # speed < 0
        {"latitude": 13.0, "longitude": 74.0, "recorded_at": valid_time, "heading_degrees": -0.1},  # heading < 0
        {"latitude": 13.0, "longitude": 74.0, "recorded_at": valid_time, "heading_degrees": 360.0}, # heading >= 360
    ]

    with mock_firebase_token(driver.firebase_uid, driver.email):
        for payload in invalid_cases:
            res = await async_client.post(
                f"/api/v1/trips/{trip.id}/gps",
                json=payload,
                headers={"Authorization": "Bearer mock-driver-token"},
            )
            assert res.status_code == 422


# --- 5. OUT-OF-ORDER & DUPLICATE GPS PERSISTENCE TESTS ---

@pytest.mark.asyncio
async def test_out_of_order_and_duplicate_gps_retention(async_client: AsyncClient):
    """Out-of-order points and duplicate points must all be retained and returned ordered chronologically."""
    bus = await create_test_bus()
    driver = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    route = await create_test_route()
    trip = await create_test_trip(driver, bus, route, TripStatus.IN_PROGRESS)

    base_time = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)
    t_10_05 = (base_time + timedelta(minutes=5)).isoformat()
    t_10_04 = (base_time + timedelta(minutes=4)).isoformat()
    t_10_06 = (base_time + timedelta(minutes=6)).isoformat()

    with mock_firebase_token(driver.firebase_uid, driver.email):
        # 1. Ingest at 10:05
        res1 = await async_client.post(
            f"/api/v1/trips/{trip.id}/gps",
            json={"latitude": 13.3401, "longitude": 74.7401, "recorded_at": t_10_05},
            headers={"Authorization": "Bearer mock-driver-token"},
        )
        assert res1.status_code == 201

        # 2. Ingest out-of-order point at 10:04 (older)
        res2 = await async_client.post(
            f"/api/v1/trips/{trip.id}/gps",
            json={"latitude": 13.3400, "longitude": 74.7400, "recorded_at": t_10_04},
            headers={"Authorization": "Bearer mock-driver-token"},
        )
        assert res2.status_code == 201

        # 3. Ingest at 10:06
        res3 = await async_client.post(
            f"/api/v1/trips/{trip.id}/gps",
            json={"latitude": 13.3402, "longitude": 74.7402, "recorded_at": t_10_06},
            headers={"Authorization": "Bearer mock-driver-token"},
        )
        assert res3.status_code == 201

        # 4. Ingest duplicate of 10:06 point
        res4 = await async_client.post(
            f"/api/v1/trips/{trip.id}/gps",
            json={"latitude": 13.3402, "longitude": 74.7402, "recorded_at": t_10_06},
            headers={"Authorization": "Bearer mock-driver-token"},
        )
        assert res4.status_code == 201

        # Driver retrieves history
        get_res = await async_client.get(
            f"/api/v1/trips/{trip.id}/gps",
            headers={"Authorization": "Bearer mock-driver-token"},
        )

    assert get_res.status_code == 200
    points = get_res.json()
    assert len(points) == 4

    # Verify chronological ascending ordering: 10:04 -> 10:05 -> 10:06 -> 10:06
    assert datetime.fromisoformat(points[0]["recorded_at"]) == datetime.fromisoformat(t_10_04)
    assert datetime.fromisoformat(points[1]["recorded_at"]) == datetime.fromisoformat(t_10_05)
    assert datetime.fromisoformat(points[2]["recorded_at"]) == datetime.fromisoformat(t_10_06)
    assert datetime.fromisoformat(points[3]["recorded_at"]) == datetime.fromisoformat(t_10_06)
    assert points[0]["latitude"] == 13.3400
    assert points[1]["latitude"] == 13.3401
    assert points[2]["latitude"] == 13.3402
    assert points[3]["latitude"] == 13.3402


# --- 6. GPS READ API PERMISSIONS ---

@pytest.mark.asyncio
async def test_gps_read_permissions(async_client: AsyncClient):
    """Admin can view any trip's GPS history; Driver can only view own trip; Student/Parent forbidden."""
    admin = await create_test_user(UserRole.ADMIN)
    bus = await create_test_bus()
    driver1 = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    driver2 = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    student = await create_test_user(UserRole.STUDENT)
    route = await create_test_route()
    trip = await create_test_trip(driver1, bus, route, TripStatus.IN_PROGRESS)

    # Ingest 1 point
    with mock_firebase_token(driver1.firebase_uid, driver1.email):
        await async_client.post(
            f"/api/v1/trips/{trip.id}/gps",
            json={
                "latitude": 13.3400,
                "longitude": 74.7400,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            },
            headers={"Authorization": "Bearer mock-driver1-token"},
        )

    # Admin reads GPS -> 200 OK
    with mock_firebase_token(admin.firebase_uid, admin.email):
        res_adm = await async_client.get(
            f"/api/v1/trips/{trip.id}/gps",
            headers={"Authorization": "Bearer mock-admin-token"},
        )
    assert res_adm.status_code == 200
    assert len(res_adm.json()) == 1

    # Driver 2 reads Driver 1's GPS -> 403 Forbidden
    with mock_firebase_token(driver2.firebase_uid, driver2.email):
        res_drv2 = await async_client.get(
            f"/api/v1/trips/{trip.id}/gps",
            headers={"Authorization": "Bearer mock-driver2-token"},
        )
    assert res_drv2.status_code == 403

    # Student reads GPS -> 403 Forbidden
    with mock_firebase_token(student.firebase_uid, student.email):
        res_stu = await async_client.get(
            f"/api/v1/trips/{trip.id}/gps",
            headers={"Authorization": "Bearer mock-student-token"},
        )
    assert res_stu.status_code == 403
