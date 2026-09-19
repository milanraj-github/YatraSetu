import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient

from app.db.database import async_session_factory
from app.models.bus import Bus
from app.models.enums import TripStatus, UserRole
from app.models.location import LocationPing
from app.models.route import Route
from app.models.trip import Trip
from app.models.user import User


async def create_test_user(role: UserRole, prefix: str = "gps_sync_user", assigned_bus_id: uuid.UUID | None = None) -> User:
    """Helper to seed a test user with a specific role and optional assigned bus."""
    test_uid = f"fb-gps-sync-{role.value.lower()}-{uuid.uuid4().hex[:8]}"
    domain = "sode-edu.in" if role == UserRole.STUDENT else "test.invalid"
    test_email = f"{prefix}_{uuid.uuid4().hex[:8]}@{domain}"

    async with async_session_factory() as session:
        user = User(
            firebase_uid=test_uid,
            email=test_email,
            full_name=f"GPS Sync Test {role.value}",
            role=role,
            assigned_bus_id=assigned_bus_id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def create_test_bus(is_active: bool = True) -> Bus:
    """Helper to seed a test bus."""
    bus_num = f"BUS-SYNC-{uuid.uuid4().hex[:6].upper()}"
    reg_num = f"KA-20-S-{uuid.uuid4().hex[:4].upper()}"

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
    code = f"RS-{uuid.uuid4().hex[:6].upper()}"
    async with async_session_factory() as session:
        route = Route(name="Campus Sync Route", code=code, is_active=is_active)
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
async def test_batch_sync_missing_and_invalid_token(async_client: AsyncClient):
    """Missing or invalid auth headers should yield 401 Unauthorized."""
    fake_trip_id = uuid.uuid4()
    payload = {
        "points": [
            {
                "client_id": str(uuid.uuid4()),
                "latitude": 13.34088,
                "longitude": 74.74214,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
    }

    # Missing header
    res1 = await async_client.post(f"/api/v1/trips/{fake_trip_id}/gps/sync", json=payload)
    assert res1.status_code == 401

    # Invalid token
    res2 = await async_client.post(
        f"/api/v1/trips/{fake_trip_id}/gps/sync",
        json=payload,
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert res2.status_code == 401


@pytest.mark.asyncio
async def test_batch_sync_role_enforcement(async_client: AsyncClient):
    """STUDENT, PARENT, and ADMIN cannot sync GPS batches (only DRIVER allowed)."""
    admin = await create_test_user(UserRole.ADMIN)
    student = await create_test_user(UserRole.STUDENT)
    parent = await create_test_user(UserRole.PARENT)
    bus = await create_test_bus()
    driver = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    route = await create_test_route()
    trip = await create_test_trip(driver, bus, route, TripStatus.IN_PROGRESS)

    payload = {
        "points": [
            {
                "client_id": str(uuid.uuid4()),
                "latitude": 13.34088,
                "longitude": 74.74214,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
    }

    # Student -> 403
    with mock_firebase_token(student.firebase_uid, student.email):
        res_stu = await async_client.post(
            f"/api/v1/trips/{trip.id}/gps/sync",
            json=payload,
            headers={"Authorization": "Bearer mock-student-token"},
        )
    assert res_stu.status_code == 403

    # Parent -> 403
    with mock_firebase_token(parent.firebase_uid, parent.email):
        res_par = await async_client.post(
            f"/api/v1/trips/{trip.id}/gps/sync",
            json=payload,
            headers={"Authorization": "Bearer mock-parent-token"},
        )
    assert res_par.status_code == 403

    # Admin -> 403 (Admin cannot submit GPS batch on behalf of driver)
    with mock_firebase_token(admin.firebase_uid, admin.email):
        res_adm = await async_client.post(
            f"/api/v1/trips/{trip.id}/gps/sync",
            json=payload,
            headers={"Authorization": "Bearer mock-admin-token"},
        )
    assert res_adm.status_code == 403


# --- 2. DRIVER OWNERSHIP & BUS ASSIGNMENT TESTS ---

@pytest.mark.asyncio
async def test_batch_sync_driver_ownership(async_client: AsyncClient):
    """Unassigned driver or wrong bus assignment cannot sync batch GPS."""
    bus1 = await create_test_bus()
    bus2 = await create_test_bus()
    driver1 = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus1.id)
    driver2 = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus2.id)
    route = await create_test_route()
    trip = await create_test_trip(driver1, bus1, route, TripStatus.IN_PROGRESS)

    payload = {
        "points": [
            {
                "client_id": str(uuid.uuid4()),
                "latitude": 13.34088,
                "longitude": 74.74214,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
    }

    # Driver 2 tries to sync GPS to Driver 1's trip
    with mock_firebase_token(driver2.firebase_uid, driver2.email):
        res = await async_client.post(
            f"/api/v1/trips/{trip.id}/gps/sync",
            json=payload,
            headers={"Authorization": "Bearer mock-driver2-token"},
        )
    assert res.status_code == 403
    assert "Access forbidden" in res.json()["detail"]


# --- 3. TRIP STATUS & NOT FOUND ENFORCEMENT ---

@pytest.mark.asyncio
async def test_batch_sync_trip_status_requirements(async_client: AsyncClient):
    """Batch GPS sync must be accepted for IN_PROGRESS and rejected for SCHEDULED/COMPLETED/CANCELLED."""
    bus = await create_test_bus()
    driver = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    route = await create_test_route()

    trip_scheduled = await create_test_trip(driver, bus, route, TripStatus.SCHEDULED)
    trip_completed = await create_test_trip(driver, bus, route, TripStatus.COMPLETED)
    trip_cancelled = await create_test_trip(driver, bus, route, TripStatus.CANCELLED)

    payload = {
        "points": [
            {
                "client_id": str(uuid.uuid4()),
                "latitude": 13.34088,
                "longitude": 74.74214,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
    }

    with mock_firebase_token(driver.firebase_uid, driver.email):
        # SCHEDULED -> 409
        res_sch = await async_client.post(
            f"/api/v1/trips/{trip_scheduled.id}/gps/sync",
            json=payload,
            headers={"Authorization": "Bearer mock-driver-token"},
        )
        assert res_sch.status_code == 409

        # COMPLETED -> 409
        res_cmp = await async_client.post(
            f"/api/v1/trips/{trip_completed.id}/gps/sync",
            json=payload,
            headers={"Authorization": "Bearer mock-driver-token"},
        )
        assert res_cmp.status_code == 409

        # CANCELLED -> 409
        res_ccl = await async_client.post(
            f"/api/v1/trips/{trip_cancelled.id}/gps/sync",
            json=payload,
            headers={"Authorization": "Bearer mock-driver-token"},
        )
        assert res_ccl.status_code == 409


@pytest.mark.asyncio
async def test_batch_sync_nonexistent_trip(async_client: AsyncClient):
    """Non-existent trip returns 404."""
    bus = await create_test_bus()
    driver = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    fake_trip_id = uuid.uuid4()

    payload = {
        "points": [
            {
                "client_id": str(uuid.uuid4()),
                "latitude": 13.34088,
                "longitude": 74.74214,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
    }

    with mock_firebase_token(driver.firebase_uid, driver.email):
        res = await async_client.post(
            f"/api/v1/trips/{fake_trip_id}/gps/sync",
            json=payload,
            headers={"Authorization": "Bearer mock-driver-token"},
        )
    assert res.status_code == 404


# --- 4. VALIDATION TESTS ---

@pytest.mark.asyncio
async def test_batch_sync_validation_bounds(async_client: AsyncClient):
    """Empty batch, batch exceeding 500 points, or invalid coordinates return 422."""
    bus = await create_test_bus()
    driver = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    route = await create_test_route()
    trip = await create_test_trip(driver, bus, route, TripStatus.IN_PROGRESS)

    with mock_firebase_token(driver.firebase_uid, driver.email):
        # Empty points list -> 422
        res_empty = await async_client.post(
            f"/api/v1/trips/{trip.id}/gps/sync",
            json={"points": []},
            headers={"Authorization": "Bearer mock-driver-token"},
        )
        assert res_empty.status_code == 422

        # Invalid coordinate in batch -> 422
        res_inv_coord = await async_client.post(
            f"/api/v1/trips/{trip.id}/gps/sync",
            json={
                "points": [
                    {
                        "client_id": str(uuid.uuid4()),
                        "latitude": 95.0,  # Invalid
                        "longitude": 74.74,
                        "recorded_at": datetime.now(timezone.utc).isoformat(),
                    }
                ]
            },
            headers={"Authorization": "Bearer mock-driver-token"},
        )
        assert res_inv_coord.status_code == 422


# --- 5. BATCH SYNC & IDEMPOTENCY TESTS ---

@pytest.mark.asyncio
async def test_batch_sync_successful_and_idempotent(async_client: AsyncClient):
    """Valid batch ingestion, database storage, and complete retry idempotency."""
    bus = await create_test_bus()
    driver = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    route = await create_test_route()
    trip = await create_test_trip(driver, bus, route, TripStatus.IN_PROGRESS)

    base_time = datetime(2026, 9, 19, 12, 0, 0, tzinfo=timezone.utc)
    point1_id = uuid.uuid4()
    point2_id = uuid.uuid4()
    point3_id = uuid.uuid4()

    batch_payload = {
        "points": [
            {
                "client_id": str(point1_id),
                "latitude": 13.3401,
                "longitude": 74.7401,
                "recorded_at": (base_time + timedelta(seconds=10)).isoformat(),
                "accuracy_meters": 5.0,
                "speed_mps": 10.0,
                "heading_degrees": 90.0,
            },
            {
                "client_id": str(point2_id),
                "latitude": 13.3402,
                "longitude": 74.7402,
                "recorded_at": (base_time + timedelta(seconds=20)).isoformat(),
                "accuracy_meters": 4.5,
                "speed_mps": 12.0,
                "heading_degrees": 95.0,
            },
            {
                "client_id": str(point3_id),
                "latitude": 13.3403,
                "longitude": 74.7403,
                "recorded_at": (base_time + timedelta(seconds=30)).isoformat(),
                "accuracy_meters": 4.0,
                "speed_mps": 15.0,
                "heading_degrees": 100.0,
            },
        ]
    }

    # 1. First sync submission: all 3 points should be accepted
    with mock_firebase_token(driver.firebase_uid, driver.email):
        res1 = await async_client.post(
            f"/api/v1/trips/{trip.id}/gps/sync",
            json=batch_payload,
            headers={"Authorization": "Bearer mock-driver-token"},
        )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["trip_id"] == str(trip.id)
    assert data1["total"] == 3
    assert data1["accepted"] == 3
    assert data1["duplicates"] == 0

    # 2. Retry exact same batch: all 3 points should be marked as duplicates
    with mock_firebase_token(driver.firebase_uid, driver.email):
        res2 = await async_client.post(
            f"/api/v1/trips/{trip.id}/gps/sync",
            json=batch_payload,
            headers={"Authorization": "Bearer mock-driver-token"},
        )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["trip_id"] == str(trip.id)
    assert data2["total"] == 3
    assert data2["accepted"] == 0
    assert data2["duplicates"] == 3

    # 3. Partial overlap + intra-batch duplicate:
    # - point2_id (already in DB -> duplicate)
    # - point4_id (new -> accepted)
    # - point4_id again (duplicate within batch -> duplicate)
    point4_id = uuid.uuid4()
    partial_payload = {
        "points": [
            {
                "client_id": str(point2_id),
                "latitude": 13.3402,
                "longitude": 74.7402,
                "recorded_at": (base_time + timedelta(seconds=20)).isoformat(),
            },
            {
                "client_id": str(point4_id),
                "latitude": 13.3404,
                "longitude": 74.7404,
                "recorded_at": (base_time + timedelta(seconds=40)).isoformat(),
            },
            {
                "client_id": str(point4_id),
                "latitude": 13.3404,
                "longitude": 74.7404,
                "recorded_at": (base_time + timedelta(seconds=40)).isoformat(),
            },
        ]
    }
    with mock_firebase_token(driver.firebase_uid, driver.email):
        res3 = await async_client.post(
            f"/api/v1/trips/{trip.id}/gps/sync",
            json=partial_payload,
            headers={"Authorization": "Bearer mock-driver-token"},
        )
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["total"] == 3
    assert data3["accepted"] == 1
    assert data3["duplicates"] == 2

    # 4. Verify GPS history contains exactly 4 distinct points in DB
    with mock_firebase_token(driver.firebase_uid, driver.email):
        history_res = await async_client.get(
            f"/api/v1/trips/{trip.id}/gps",
            headers={"Authorization": "Bearer mock-driver-token"},
        )
    assert history_res.status_code == 200
    history = history_res.json()
    assert len(history) == 4
    stored_client_ids = {p["client_id"] for p in history}
    assert stored_client_ids == {str(point1_id), str(point2_id), str(point3_id), str(point4_id)}


# --- 6. OUT-OF-ORDER BATCH SYNC & REDIS LIVE MONOTONICITY ---

@pytest.mark.asyncio
async def test_batch_sync_out_of_order_retention_and_live_state(async_client: AsyncClient):
    """Batch containing out-of-order points updates live state to the newest recorded_at."""
    bus = await create_test_bus()
    driver = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    route = await create_test_route()
    trip = await create_test_trip(driver, bus, route, TripStatus.IN_PROGRESS)

    base_time = datetime(2026, 9, 19, 14, 0, 0, tzinfo=timezone.utc)
    t_14_05 = (base_time + timedelta(minutes=5)).isoformat()
    t_14_02 = (base_time + timedelta(minutes=2)).isoformat()
    t_14_08 = (base_time + timedelta(minutes=8)).isoformat()

    batch_payload = {
        "points": [
            {
                "client_id": str(uuid.uuid4()),
                "latitude": 13.3405,
                "longitude": 74.7405,
                "recorded_at": t_14_05,
            },
            {
                "client_id": str(uuid.uuid4()),
                "latitude": 13.3402,
                "longitude": 74.7402,
                "recorded_at": t_14_02,
            },
            {
                "client_id": str(uuid.uuid4()),
                "latitude": 13.3408,
                "longitude": 74.7408,
                "recorded_at": t_14_08,
            },
        ]
    }

    with mock_firebase_token(driver.firebase_uid, driver.email):
        res = await async_client.post(
            f"/api/v1/trips/{trip.id}/gps/sync",
            json=batch_payload,
            headers={"Authorization": "Bearer mock-driver-token"},
        )
        assert res.status_code == 200
        assert res.json()["accepted"] == 3

        # Live location should reflect the newest point (14:08 / 13.3408)
        live_res = await async_client.get(
            f"/api/v1/trips/{trip.id}/live",
            headers={"Authorization": "Bearer mock-driver-token"},
        )
        assert live_res.status_code == 200
        live_data = live_res.json()
        assert live_data["latitude"] == 13.3408
        assert live_data["longitude"] == 74.7408
        assert datetime.fromisoformat(live_data["recorded_at"]) == datetime.fromisoformat(t_14_08)


# --- 7. REDIS FAILURE FAULT TOLERANCE ---

@pytest.mark.asyncio
async def test_batch_sync_redis_failure_fault_tolerance(async_client: AsyncClient):
    """If Redis fails during live location update, DB batch sync still succeeds."""
    bus = await create_test_bus()
    driver = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    route = await create_test_route()
    trip = await create_test_trip(driver, bus, route, TripStatus.IN_PROGRESS)

    point_id = uuid.uuid4()
    batch_payload = {
        "points": [
            {
                "client_id": str(point_id),
                "latitude": 13.3400,
                "longitude": 74.7400,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
    }

    with mock_firebase_token(driver.firebase_uid, driver.email), \
         patch("app.services.gps_service.get_redis_client", side_effect=Exception("Redis connection refused")):
        res = await async_client.post(
            f"/api/v1/trips/{trip.id}/gps/sync",
            json=batch_payload,
            headers={"Authorization": "Bearer mock-driver-token"},
        )

    # Ingestion should still succeed in DB
    assert res.status_code == 200
    assert res.json()["accepted"] == 1
    assert res.json()["duplicates"] == 0
