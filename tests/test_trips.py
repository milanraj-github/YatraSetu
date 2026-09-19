import uuid
from datetime import datetime, timezone
from unittest.mock import patch
import pytest
from httpx import AsyncClient

from app.db.database import async_session_factory
from app.models.bus import Bus
from app.models.enums import TripStatus, UserRole
from app.models.route import Route
from app.models.trip import Trip
from app.models.user import User


async def create_test_user(role: UserRole, prefix: str = "trip_user", assigned_bus_id: uuid.UUID | None = None) -> User:
    """Helper to seed a test user with a specific role and optional assigned bus."""
    test_uid = f"fb-trip-{role.value.lower()}-{uuid.uuid4().hex[:8]}"
    domain = "sode-edu.in" if role == UserRole.STUDENT else "test.invalid"
    test_email = f"{prefix}_{uuid.uuid4().hex[:8]}@{domain}"

    async with async_session_factory() as session:
        user = User(
            firebase_uid=test_uid,
            email=test_email,
            full_name=f"Trip Test {role.value}",
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
        route = Route(name="Campus Main Route", code=code, is_active=is_active)
        session.add(route)
        await session.commit()
        await session.refresh(route)
        return route


def mock_firebase_token(uid: str, email: str):
    return patch(
        "app.core.security.verify_firebase_token",
        return_value={"uid": uid, "email": email},
    )


# --- 1. TRIP CREATION TESTS ---

@pytest.mark.asyncio
async def test_admin_can_create_trip(async_client: AsyncClient):
    """Admin creates a trip when driver is assigned to the specified bus."""
    admin = await create_test_user(UserRole.ADMIN)
    bus = await create_test_bus(is_active=True)
    driver = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    route = await create_test_route(is_active=True)

    payload = {
        "route_id": str(route.id),
        "bus_id": str(bus.id),
        "driver_id": str(driver.id),
        "scheduled_start_at": datetime.now(timezone.utc).isoformat(),
    }

    with mock_firebase_token(admin.firebase_uid, admin.email):
        response = await async_client.post(
            "/api/v1/trips",
            json=payload,
            headers={"Authorization": "Bearer mock-admin-token"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["route_id"] == str(route.id)
    assert data["bus_id"] == str(bus.id)
    assert data["driver_id"] == str(driver.id)
    assert data["status"] == TripStatus.SCHEDULED.value
    assert data["actual_start_at"] is None
    assert data["actual_end_at"] is None


@pytest.mark.asyncio
async def test_create_trip_unassigned_driver_conflict(async_client: AsyncClient):
    """Trip creation fails with 409 Conflict if driver is not assigned to the bus."""
    admin = await create_test_user(UserRole.ADMIN)
    bus1 = await create_test_bus(is_active=True)
    bus2 = await create_test_bus(is_active=True)
    driver = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus1.id)
    route = await create_test_route(is_active=True)

    payload = {
        "route_id": str(route.id),
        "bus_id": str(bus2.id),
        "driver_id": str(driver.id),
    }

    with mock_firebase_token(admin.firebase_uid, admin.email):
        response = await async_client.post(
            "/api/v1/trips",
            json=payload,
            headers={"Authorization": "Bearer mock-admin-token"},
        )

    assert response.status_code == 409
    assert "not assigned" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_trip_inactive_route_or_bus(async_client: AsyncClient):
    """Creating a trip with inactive route or bus returns 400 Bad Request."""
    admin = await create_test_user(UserRole.ADMIN)
    inactive_bus = await create_test_bus(is_active=False)
    driver = await create_test_user(UserRole.DRIVER, assigned_bus_id=inactive_bus.id)
    active_route = await create_test_route(is_active=True)

    with mock_firebase_token(admin.firebase_uid, admin.email):
        res1 = await async_client.post(
            "/api/v1/trips",
            json={
                "route_id": str(active_route.id),
                "bus_id": str(inactive_bus.id),
                "driver_id": str(driver.id),
            },
            headers={"Authorization": "Bearer mock-admin-token"},
        )
    assert res1.status_code == 400
    assert "inactive bus" in res1.json()["detail"]

    active_bus = await create_test_bus(is_active=True)
    driver2 = await create_test_user(UserRole.DRIVER, assigned_bus_id=active_bus.id)
    inactive_route = await create_test_route(is_active=False)

    with mock_firebase_token(admin.firebase_uid, admin.email):
        res2 = await async_client.post(
            "/api/v1/trips",
            json={
                "route_id": str(inactive_route.id),
                "bus_id": str(active_bus.id),
                "driver_id": str(driver2.id),
            },
            headers={"Authorization": "Bearer mock-admin-token"},
        )
    assert res2.status_code == 400
    assert "inactive route" in res2.json()["detail"]


# --- 2. TRIP LIST & DETAIL TESTS ---

@pytest.mark.asyncio
async def test_driver_only_sees_own_trips(async_client: AsyncClient):
    """Driver list only contains trips where driver_id == current_user.id."""
    admin = await create_test_user(UserRole.ADMIN)
    bus1 = await create_test_bus()
    bus2 = await create_test_bus()
    driver1 = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus1.id)
    driver2 = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus2.id)
    route = await create_test_route()

    # Create trip for driver 1 and trip for driver 2
    with mock_firebase_token(admin.firebase_uid, admin.email):
        await async_client.post(
            "/api/v1/trips",
            json={"route_id": str(route.id), "bus_id": str(bus1.id), "driver_id": str(driver1.id)},
            headers={"Authorization": "Bearer mock-admin-token"},
        )
        res2 = await async_client.post(
            "/api/v1/trips",
            json={"route_id": str(route.id), "bus_id": str(bus2.id), "driver_id": str(driver2.id)},
            headers={"Authorization": "Bearer mock-admin-token"},
        )
        trip2_id = res2.json()["id"]

    # Driver 1 lists trips
    with mock_firebase_token(driver1.firebase_uid, driver1.email):
        list_res = await async_client.get(
            "/api/v1/trips",
            headers={"Authorization": "Bearer mock-driver-token"},
        )
        # Driver 1 tries to get trip 2 details
        detail_res = await async_client.get(
            f"/api/v1/trips/{trip2_id}",
            headers={"Authorization": "Bearer mock-driver-token"},
        )

    assert list_res.status_code == 200
    trips = list_res.json()
    assert all(t["driver_id"] == str(driver1.id) for t in trips)
    assert detail_res.status_code == 403


# --- 3. TRIP LIFECYCLE TESTS (START / END / CANCEL) ---

@pytest.mark.asyncio
async def test_trip_full_lifecycle(async_client: AsyncClient):
    """Driver starts trip (SCHEDULED -> IN_PROGRESS) then ends trip (IN_PROGRESS -> COMPLETED)."""
    admin = await create_test_user(UserRole.ADMIN)
    bus = await create_test_bus()
    driver = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    route = await create_test_route()

    # Admin creates trip
    with mock_firebase_token(admin.firebase_uid, admin.email):
        res = await async_client.post(
            "/api/v1/trips",
            json={"route_id": str(route.id), "bus_id": str(bus.id), "driver_id": str(driver.id)},
            headers={"Authorization": "Bearer mock-admin-token"},
        )
    trip_id = res.json()["id"]

    # Driver starts trip
    with mock_firebase_token(driver.firebase_uid, driver.email):
        start_res = await async_client.post(
            f"/api/v1/trips/{trip_id}/start",
            headers={"Authorization": "Bearer mock-driver-token"},
        )
    assert start_res.status_code == 200
    start_data = start_res.json()
    assert start_data["status"] == TripStatus.IN_PROGRESS.value
    assert start_data["actual_start_at"] is not None

    # Driver ends trip
    with mock_firebase_token(driver.firebase_uid, driver.email):
        end_res = await async_client.post(
            f"/api/v1/trips/{trip_id}/end",
            headers={"Authorization": "Bearer mock-driver-token"},
        )
    assert end_res.status_code == 200
    end_data = end_res.json()
    assert end_data["status"] == TripStatus.COMPLETED.value
    assert end_data["actual_end_at"] is not None


@pytest.mark.asyncio
async def test_invalid_lifecycle_transitions(async_client: AsyncClient):
    """Cannot start a completed trip or end a scheduled trip."""
    admin = await create_test_user(UserRole.ADMIN)
    bus = await create_test_bus()
    driver = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    route = await create_test_route()

    with mock_firebase_token(admin.firebase_uid, admin.email):
        res = await async_client.post(
            "/api/v1/trips",
            json={"route_id": str(route.id), "bus_id": str(bus.id), "driver_id": str(driver.id)},
            headers={"Authorization": "Bearer mock-admin-token"},
        )
        trip_id = res.json()["id"]

        # Attempt to end a scheduled trip directly
        end_res = await async_client.post(
            f"/api/v1/trips/{trip_id}/end",
            headers={"Authorization": "Bearer mock-admin-token"},
        )
    assert end_res.status_code == 409
    assert "Cannot end trip" in end_res.json()["detail"]


@pytest.mark.asyncio
async def test_cancel_trip(async_client: AsyncClient):
    """Admin can cancel SCHEDULED trip; Driver cannot cancel trips."""
    admin = await create_test_user(UserRole.ADMIN)
    bus = await create_test_bus()
    driver = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    route = await create_test_route()

    with mock_firebase_token(admin.firebase_uid, admin.email):
        res = await async_client.post(
            "/api/v1/trips",
            json={"route_id": str(route.id), "bus_id": str(bus.id), "driver_id": str(driver.id)},
            headers={"Authorization": "Bearer mock-admin-token"},
        )
    trip_id = res.json()["id"]

    # Driver attempts to cancel
    with mock_firebase_token(driver.firebase_uid, driver.email):
        driver_cancel = await async_client.post(
            f"/api/v1/trips/{trip_id}/cancel",
            headers={"Authorization": "Bearer mock-driver-token"},
        )
    assert driver_cancel.status_code == 403

    # Admin cancels
    with mock_firebase_token(admin.firebase_uid, admin.email):
        admin_cancel = await async_client.post(
            f"/api/v1/trips/{trip_id}/cancel",
            headers={"Authorization": "Bearer mock-admin-token"},
        )
    assert admin_cancel.status_code == 200
    assert admin_cancel.json()["status"] == TripStatus.CANCELLED.value


@pytest.mark.asyncio
async def test_driver_cannot_operate_trip_if_bus_unassigned(async_client: AsyncClient):
    """If a driver's assigned_bus_id is removed or changed, they cannot start the trip."""
    admin = await create_test_user(UserRole.ADMIN)
    bus1 = await create_test_bus()
    bus2 = await create_test_bus()
    driver = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus1.id)
    route = await create_test_route()

    # Admin creates trip with bus1
    with mock_firebase_token(admin.firebase_uid, admin.email):
        res = await async_client.post(
            "/api/v1/trips",
            json={"route_id": str(route.id), "bus_id": str(bus1.id), "driver_id": str(driver.id)},
            headers={"Authorization": "Bearer mock-admin-token"},
        )
        trip_id = res.json()["id"]

        # Admin reassigns driver to bus2
        await async_client.post(
            f"/api/v1/drivers/{driver.id}/assign-bus/{bus2.id}",
            headers={"Authorization": "Bearer mock-admin-token"},
        )

    # Driver attempts to start trip for bus1
    with mock_firebase_token(driver.firebase_uid, driver.email):
        start_res = await async_client.post(
            f"/api/v1/trips/{trip_id}/start",
            headers={"Authorization": "Bearer mock-driver-token"},
        )
    assert start_res.status_code == 403
    assert "driver ownership mismatch" in start_res.json()["detail"]
