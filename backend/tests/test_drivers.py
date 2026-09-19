import uuid
from unittest.mock import patch
import pytest
from httpx import AsyncClient

from app.db.database import async_session_factory
from app.models.bus import Bus
from app.models.enums import UserRole
from app.models.user import User


async def create_test_user(role: UserRole, prefix: str = "driver_user") -> User:
    """Helper to seed a test user with a specific role."""
    test_uid = f"fb-drv-{role.value.lower()}-{uuid.uuid4().hex[:8]}"
    domain = "sode-edu.in" if role == UserRole.STUDENT else "test.invalid"
    test_email = f"{prefix}_{uuid.uuid4().hex[:8]}@{domain}"

    async with async_session_factory() as session:
        user = User(
            firebase_uid=test_uid,
            email=test_email,
            full_name=f"Driver Test {role.value}",
            role=role,
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


def mock_firebase_token(uid: str, email: str):
    return patch(
        "app.core.security.verify_firebase_token",
        return_value={"uid": uid, "email": email},
    )


# --- 1. BUS ASSIGNMENT TESTS ---

@pytest.mark.asyncio
async def test_admin_can_assign_bus_to_driver(async_client: AsyncClient):
    """Admin successfully assigns an active bus to a driver."""
    admin = await create_test_user(UserRole.ADMIN)
    driver = await create_test_user(UserRole.DRIVER)
    bus = await create_test_bus(is_active=True)

    with mock_firebase_token(admin.firebase_uid, admin.email):
        response = await async_client.post(
            f"/api/v1/drivers/{driver.id}/assign-bus/{bus.id}",
            headers={"Authorization": "Bearer mock-admin-token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["driver_id"] == str(driver.id)
    assert data["assigned_bus_id"] == str(bus.id)
    assert data["assigned_bus_number"] == bus.bus_number
    assert data["assigned_bus_registration"] == bus.registration_number


@pytest.mark.asyncio
async def test_assign_bus_to_non_driver_fails(async_client: AsyncClient):
    """Assigning a bus to a student/parent/admin user should return 400 Bad Request."""
    admin = await create_test_user(UserRole.ADMIN)
    student = await create_test_user(UserRole.STUDENT)
    bus = await create_test_bus(is_active=True)

    with mock_firebase_token(admin.firebase_uid, admin.email):
        response = await async_client.post(
            f"/api/v1/drivers/{student.id}/assign-bus/{bus.id}",
            headers={"Authorization": "Bearer mock-admin-token"},
        )

    assert response.status_code == 400
    assert "User is not a driver" in response.json()["detail"]


@pytest.mark.asyncio
async def test_assign_inactive_bus_fails(async_client: AsyncClient):
    """Assigning an inactive bus should return 400 Bad Request."""
    admin = await create_test_user(UserRole.ADMIN)
    driver = await create_test_user(UserRole.DRIVER)
    bus = await create_test_bus(is_active=False)

    with mock_firebase_token(admin.firebase_uid, admin.email):
        response = await async_client.post(
            f"/api/v1/drivers/{driver.id}/assign-bus/{bus.id}",
            headers={"Authorization": "Bearer mock-admin-token"},
        )

    assert response.status_code == 400
    assert "Cannot assign an inactive bus" in response.json()["detail"]


@pytest.mark.asyncio
async def test_assign_nonexistent_driver_or_bus_fails(async_client: AsyncClient):
    """Assigning a non-existent driver or bus should return 404."""
    admin = await create_test_user(UserRole.ADMIN)
    driver = await create_test_user(UserRole.DRIVER)
    fake_id = uuid.uuid4()

    with mock_firebase_token(admin.firebase_uid, admin.email):
        res1 = await async_client.post(
            f"/api/v1/drivers/{fake_id}/assign-bus/{fake_id}",
            headers={"Authorization": "Bearer mock-admin-token"},
        )
        res2 = await async_client.post(
            f"/api/v1/drivers/{driver.id}/assign-bus/{fake_id}",
            headers={"Authorization": "Bearer mock-admin-token"},
        )

    assert res1.status_code == 404
    assert res2.status_code == 404


@pytest.mark.asyncio
async def test_driver_cannot_assign_bus(async_client: AsyncClient):
    """Driver attempting to assign a bus should receive 403 Forbidden."""
    driver = await create_test_user(UserRole.DRIVER)
    bus = await create_test_bus(is_active=True)

    with mock_firebase_token(driver.firebase_uid, driver.email):
        response = await async_client.post(
            f"/api/v1/drivers/{driver.id}/assign-bus/{bus.id}",
            headers={"Authorization": "Bearer mock-driver-token"},
        )

    assert response.status_code == 403


# --- 2. BUS UNASSIGNMENT TESTS ---

@pytest.mark.asyncio
async def test_admin_can_unassign_bus(async_client: AsyncClient):
    """Admin successfully unassigns a bus from a driver."""
    admin = await create_test_user(UserRole.ADMIN)
    driver = await create_test_user(UserRole.DRIVER)
    bus = await create_test_bus(is_active=True)

    # First assign
    with mock_firebase_token(admin.firebase_uid, admin.email):
        assign_res = await async_client.post(
            f"/api/v1/drivers/{driver.id}/assign-bus/{bus.id}",
            headers={"Authorization": "Bearer mock-admin-token"},
        )
        assert assign_res.status_code == 200

        # Then unassign
        unassign_res = await async_client.delete(
            f"/api/v1/drivers/{driver.id}/unassign-bus",
            headers={"Authorization": "Bearer mock-admin-token"},
        )

    assert unassign_res.status_code == 200
    data = unassign_res.json()
    assert data["driver_id"] == str(driver.id)
    assert data["assigned_bus_id"] is None
    assert data["assigned_bus_number"] is None


@pytest.mark.asyncio
async def test_unassign_driver_without_bus_fails(async_client: AsyncClient):
    """Unassigning a driver who has no bus assigned returns 400 Bad Request."""
    admin = await create_test_user(UserRole.ADMIN)
    driver = await create_test_user(UserRole.DRIVER)

    with mock_firebase_token(admin.firebase_uid, admin.email):
        response = await async_client.delete(
            f"/api/v1/drivers/{driver.id}/unassign-bus",
            headers={"Authorization": "Bearer mock-admin-token"},
        )

    assert response.status_code == 400
    assert "Driver has no assigned bus" in response.json()["detail"]


# --- 3. GET DRIVER ASSIGNMENT TESTS ---

@pytest.mark.asyncio
async def test_get_driver_assignment(async_client: AsyncClient):
    """Admin and Driver can query driver assignment."""
    admin = await create_test_user(UserRole.ADMIN)
    driver = await create_test_user(UserRole.DRIVER)
    bus = await create_test_bus(is_active=True)

    # Assign bus
    with mock_firebase_token(admin.firebase_uid, admin.email):
        await async_client.post(
            f"/api/v1/drivers/{driver.id}/assign-bus/{bus.id}",
            headers={"Authorization": "Bearer mock-admin-token"},
        )

    # Driver retrieves their assignment
    with mock_firebase_token(driver.firebase_uid, driver.email):
        response = await async_client.get(
            f"/api/v1/drivers/{driver.id}/assignment",
            headers={"Authorization": "Bearer mock-driver-token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["driver_id"] == str(driver.id)
    assert data["assigned_bus_id"] == str(bus.id)
    assert data["assigned_bus_number"] == bus.bus_number
