import uuid
from unittest.mock import patch
import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from httpx import AsyncClient

from app.db.database import async_session_factory
from app.models.bus import Bus
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.bus import BusCreate, BusUpdate


async def create_test_user(role: UserRole, prefix: str = "user") -> User:
    """Helper to seed a test user with a given role."""
    test_uid = f"fb-bus-{role.value.lower()}-{uuid.uuid4().hex[:8]}"
    domain = "sode-edu.in" if role == UserRole.STUDENT else "test.invalid"
    test_email = f"{prefix}_{uuid.uuid4().hex[:8]}@{domain}"

    async with async_session_factory() as session:
        user = User(
            firebase_uid=test_uid,
            email=test_email,
            full_name=f"Bus Test {role.value}",
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


# --- 1. MODEL & DATABASE CONSTRAINT TESTS ---

@pytest.mark.asyncio
async def test_bus_model_creation_and_defaults():
    """Verify Bus model creates successfully with expected defaults."""
    bus_num = f"BUS-{uuid.uuid4().hex[:6].upper()}"
    reg_num = f"KA-20-{uuid.uuid4().hex[:4].upper()}"

    async with async_session_factory() as session:
        bus = Bus(
            bus_number=bus_num,
            registration_number=reg_num,
            capacity=40,
        )
        session.add(bus)
        await session.commit()
        await session.refresh(bus)

        assert bus.id is not None
        assert bus.bus_number == bus_num
        assert bus.registration_number == reg_num
        assert bus.capacity == 40
        assert bus.is_active is True
        assert bus.created_at is not None
        assert bus.updated_at is not None


@pytest.mark.asyncio
async def test_bus_unique_constraints():
    """Duplicate bus_number or registration_number must raise IntegrityError."""
    bus_num = f"BUS-{uuid.uuid4().hex[:6].upper()}"
    reg_num = f"KA-20-{uuid.uuid4().hex[:4].upper()}"

    async with async_session_factory() as session:
        bus1 = Bus(bus_number=bus_num, registration_number=reg_num, capacity=30)
        session.add(bus1)
        await session.commit()

    # Duplicate bus_number
    async with async_session_factory() as session:
        bus2 = Bus(bus_number=bus_num, registration_number=f"OTHER-{uuid.uuid4().hex[:4]}", capacity=30)
        session.add(bus2)
        with pytest.raises(IntegrityError):
            await session.commit()


# --- 2. PYDANTIC SCHEMA VALIDATION TESTS ---

def test_bus_schema_validation_success():
    """Valid BusCreate payload should succeed."""
    payload = BusCreate(
        bus_number="  BUS-01  ",
        registration_number="  KA-20-B-1234  ",
        capacity=50,
        is_active=True,
    )
    assert payload.bus_number == "BUS-01"
    assert payload.registration_number == "KA-20-B-1234"
    assert payload.capacity == 50


def test_bus_schema_blank_identifier_rejected():
    """Blank or whitespace-only bus identifiers must be rejected."""
    with pytest.raises(ValidationError):
        BusCreate(bus_number="   ", registration_number="KA-20-1234", capacity=30)

    with pytest.raises(ValidationError):
        BusCreate(bus_number="BUS-01", registration_number="", capacity=30)


def test_bus_schema_invalid_capacity_rejected():
    """Capacity <= 0 must be rejected."""
    with pytest.raises(ValidationError):
        BusCreate(bus_number="BUS-01", registration_number="KA-20-1234", capacity=0)

    with pytest.raises(ValidationError):
        BusCreate(bus_number="BUS-01", registration_number="KA-20-1234", capacity=-5)


# --- 3. API CRUD & RBAC TESTS ---

@pytest.mark.asyncio
async def test_create_bus_admin_success(async_client: AsyncClient):
    """ADMIN can create a new bus (201 Created)."""
    admin = await create_test_user(UserRole.ADMIN, "admin_create")
    bus_num = f"BUS-{uuid.uuid4().hex[:6].upper()}"
    reg_num = f"KA-20-{uuid.uuid4().hex[:4].upper()}"

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": admin.firebase_uid, "email": admin.email}
        response = await async_client.post(
            "/api/v1/buses",
            json={
                "bus_number": bus_num,
                "registration_number": reg_num,
                "capacity": 45,
            },
            headers={"Authorization": "Bearer admin-token"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["bus_number"] == bus_num
        assert data["registration_number"] == reg_num
        assert data["capacity"] == 45
        assert data["is_active"] is True
        assert "id" in data


@pytest.mark.asyncio
async def test_create_bus_non_admin_forbidden(async_client: AsyncClient):
    """DRIVER, STUDENT, and PARENT cannot create a bus (403 Forbidden)."""
    for role in [UserRole.DRIVER, UserRole.STUDENT, UserRole.PARENT]:
        user = await create_test_user(role, f"user_{role.value.lower()}")
        with patch("app.core.security.verify_firebase_token") as mock_verify:
            mock_verify.return_value = {"uid": user.firebase_uid, "email": user.email}
            response = await async_client.post(
                "/api/v1/buses",
                json={
                    "bus_number": f"BUS-{uuid.uuid4().hex[:6]}",
                    "registration_number": f"KA-{uuid.uuid4().hex[:4]}",
                    "capacity": 35,
                },
                headers={"Authorization": "Bearer user-token"},
            )
            assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_bus_duplicate_rejected(async_client: AsyncClient):
    """Creating a bus with duplicate bus_number or registration_number returns 409 Conflict."""
    admin = await create_test_user(UserRole.ADMIN, "admin_dup")
    bus_num = f"BUS-{uuid.uuid4().hex[:6].upper()}"
    reg_num = f"KA-20-{uuid.uuid4().hex[:4].upper()}"

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": admin.firebase_uid, "email": admin.email}
        # First creation
        r1 = await async_client.post(
            "/api/v1/buses",
            json={"bus_number": bus_num, "registration_number": reg_num, "capacity": 40},
            headers={"Authorization": "Bearer admin-token"},
        )
        assert r1.status_code == 201

        # Duplicate bus_number
        r2 = await async_client.post(
            "/api/v1/buses",
            json={"bus_number": bus_num, "registration_number": f"KA-DIFF-{uuid.uuid4().hex[:4]}", "capacity": 40},
            headers={"Authorization": "Bearer admin-token"},
        )
        assert r2.status_code == 409
        assert "already exists" in r2.json()["detail"]


@pytest.mark.asyncio
async def test_list_and_get_buses(async_client: AsyncClient):
    """ADMIN can list buses and retrieve bus by ID (200 OK)."""
    admin = await create_test_user(UserRole.ADMIN, "admin_read")
    bus_num = f"BUS-{uuid.uuid4().hex[:6].upper()}"
    reg_num = f"KA-20-{uuid.uuid4().hex[:4].upper()}"

    async with async_session_factory() as session:
        bus = Bus(bus_number=bus_num, registration_number=reg_num, capacity=50)
        session.add(bus)
        await session.commit()
        await session.refresh(bus)
        bus_id = str(bus.id)

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": admin.firebase_uid, "email": admin.email}

        # List
        r_list = await async_client.get("/api/v1/buses", headers={"Authorization": "Bearer admin-token"})
        assert r_list.status_code == 200
        assert isinstance(r_list.json(), list)
        assert any(b["id"] == bus_id for b in r_list.json())

        # Get by ID
        r_get = await async_client.get(f"/api/v1/buses/{bus_id}", headers={"Authorization": "Bearer admin-token"})
        assert r_get.status_code == 200
        assert r_get.json()["id"] == bus_id
        assert r_get.json()["bus_number"] == bus_num


@pytest.mark.asyncio
async def test_get_nonexistent_bus_returns_404(async_client: AsyncClient):
    """Querying a non-existent bus returns 404 Not Found."""
    admin = await create_test_user(UserRole.ADMIN, "admin_404")
    non_existent_id = uuid.uuid4()

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": admin.firebase_uid, "email": admin.email}
        response = await async_client.get(
            f"/api/v1/buses/{non_existent_id}",
            headers={"Authorization": "Bearer admin-token"},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Bus not found"


@pytest.mark.asyncio
async def test_update_bus_admin(async_client: AsyncClient):
    """ADMIN can update bus details (200 OK)."""
    admin = await create_test_user(UserRole.ADMIN, "admin_update")

    async with async_session_factory() as session:
        bus = Bus(
            bus_number=f"BUS-{uuid.uuid4().hex[:6].upper()}",
            registration_number=f"KA-{uuid.uuid4().hex[:4].upper()}",
            capacity=30,
        )
        session.add(bus)
        await session.commit()
        await session.refresh(bus)
        bus_id = str(bus.id)

    new_bus_num = f"BUS-UPDATED-{uuid.uuid4().hex[:4].upper()}"

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": admin.firebase_uid, "email": admin.email}
        response = await async_client.patch(
            f"/api/v1/buses/{bus_id}",
            json={"bus_number": new_bus_num, "capacity": 60},
            headers={"Authorization": "Bearer admin-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["bus_number"] == new_bus_num
        assert data["capacity"] == 60


@pytest.mark.asyncio
async def test_deactivate_bus_admin(async_client: AsyncClient):
    """ADMIN can safely deactivate a bus (204 No Content, sets is_active=False)."""
    admin = await create_test_user(UserRole.ADMIN, "admin_delete")

    async with async_session_factory() as session:
        bus = Bus(
            bus_number=f"BUS-{uuid.uuid4().hex[:6].upper()}",
            registration_number=f"KA-{uuid.uuid4().hex[:4].upper()}",
            capacity=40,
            is_active=True,
        )
        session.add(bus)
        await session.commit()
        await session.refresh(bus)
        bus_id = str(bus.id)

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": admin.firebase_uid, "email": admin.email}

        # DELETE /api/v1/buses/{bus_id}
        response = await async_client.delete(
            f"/api/v1/buses/{bus_id}",
            headers={"Authorization": "Bearer admin-token"},
        )
        assert response.status_code == 204

    # Verify is_active is now False in DB
    async with async_session_factory() as session:
        refreshed_bus = await session.get(Bus, uuid.UUID(bus_id))
        assert refreshed_bus is not None
        assert refreshed_bus.is_active is False
