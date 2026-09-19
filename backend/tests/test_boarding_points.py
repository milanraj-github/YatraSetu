import uuid
from unittest.mock import patch
import pytest
from pydantic import ValidationError
from httpx import AsyncClient

from app.db.database import async_session_factory
from app.models.boarding_point import BoardingPoint
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.boarding_point import BoardingPointCreate


async def create_test_user(role: UserRole, prefix: str = "user") -> User:
    """Helper to seed a test user with a specific role."""
    test_uid = f"fb-bp-{role.value.lower()}-{uuid.uuid4().hex[:8]}"
    domain = "sode-edu.in" if role == UserRole.STUDENT else "test.invalid"
    test_email = f"{prefix}_{uuid.uuid4().hex[:8]}@{domain}"

    async with async_session_factory() as session:
        user = User(
            firebase_uid=test_uid,
            email=test_email,
            full_name=f"BP Test {role.value}",
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


# --- 1. MODEL & SCHEMA VALIDATION TESTS ---

@pytest.mark.asyncio
async def test_boarding_point_model_creation():
    """Verify BoardingPoint model creates successfully."""
    async with async_session_factory() as session:
        bp = BoardingPoint(
            name="Main Gate Stop",
            latitude=13.3408,
            longitude=74.7421,
            address="Near College Campus Gate 1",
        )
        session.add(bp)
        await session.commit()
        await session.refresh(bp)

        assert bp.id is not None
        assert bp.name == "Main Gate Stop"
        assert bp.latitude == 13.3408
        assert bp.longitude == 74.7421
        assert bp.is_active is True
        assert bp.created_at is not None


def test_boarding_point_coordinates_validation():
    """Invalid latitude or longitude must be rejected."""
    # Latitude out of bounds
    with pytest.raises(ValidationError):
        BoardingPointCreate(name="Stop", latitude=95.0, longitude=74.0)

    with pytest.raises(ValidationError):
        BoardingPointCreate(name="Stop", latitude=-95.0, longitude=74.0)

    # Longitude out of bounds
    with pytest.raises(ValidationError):
        BoardingPointCreate(name="Stop", latitude=13.0, longitude=185.0)

    with pytest.raises(ValidationError):
        BoardingPointCreate(name="Stop", latitude=13.0, longitude=-190.0)

    # Blank name
    with pytest.raises(ValidationError):
        BoardingPointCreate(name="   ", latitude=13.0, longitude=74.0)


# --- 2. API CRUD & RBAC TESTS ---

@pytest.mark.asyncio
async def test_create_boarding_point_admin(async_client: AsyncClient):
    """ADMIN can create a boarding point (201 Created)."""
    admin = await create_test_user(UserRole.ADMIN, "admin_bp_create")

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": admin.firebase_uid, "email": admin.email}
        response = await async_client.post(
            "/api/v1/boarding-points",
            json={
                "name": "Hostel Block A Stop",
                "latitude": 13.3420,
                "longitude": 74.7450,
                "address": "Opposite Hostel Block A",
            },
            headers={"Authorization": "Bearer admin-token"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Hostel Block A Stop"
        assert data["latitude"] == 13.3420
        assert data["longitude"] == 74.7450
        assert "id" in data


@pytest.mark.asyncio
async def test_create_boarding_point_non_admin_forbidden(async_client: AsyncClient):
    """Non-admin roles cannot create boarding points (403 Forbidden)."""
    for role in [UserRole.DRIVER, UserRole.STUDENT, UserRole.PARENT]:
        user = await create_test_user(role, f"bp_user_{role.value.lower()}")
        with patch("app.core.security.verify_firebase_token") as mock_verify:
            mock_verify.return_value = {"uid": user.firebase_uid, "email": user.email}
            response = await async_client.post(
                "/api/v1/boarding-points",
                json={"name": "Forbidden Stop", "latitude": 13.0, "longitude": 74.0},
                headers={"Authorization": "Bearer user-token"},
            )
            assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_and_get_boarding_points(async_client: AsyncClient):
    """ADMIN can list boarding points and retrieve details (200 OK)."""
    admin = await create_test_user(UserRole.ADMIN, "admin_bp_read")

    async with async_session_factory() as session:
        bp = BoardingPoint(name="Library Stop", latitude=13.3415, longitude=74.7430)
        session.add(bp)
        await session.commit()
        await session.refresh(bp)
        bp_id = str(bp.id)

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": admin.firebase_uid, "email": admin.email}

        # List
        r_list = await async_client.get("/api/v1/boarding-points", headers={"Authorization": "Bearer admin-token"})
        assert r_list.status_code == 200
        assert any(b["id"] == bp_id for b in r_list.json())

        # Get by ID
        r_get = await async_client.get(f"/api/v1/boarding-points/{bp_id}", headers={"Authorization": "Bearer admin-token"})
        assert r_get.status_code == 200
        assert r_get.json()["name"] == "Library Stop"


@pytest.mark.asyncio
async def test_update_and_deactivate_boarding_point(async_client: AsyncClient):
    """ADMIN can update boarding point details and safely deactivate."""
    admin = await create_test_user(UserRole.ADMIN, "admin_bp_update")

    async with async_session_factory() as session:
        bp = BoardingPoint(name="Old Stop", latitude=13.3400, longitude=74.7400)
        session.add(bp)
        await session.commit()
        await session.refresh(bp)
        bp_id = str(bp.id)

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": admin.firebase_uid, "email": admin.email}

        # Update
        r_patch = await async_client.patch(
            f"/api/v1/boarding-points/{bp_id}",
            json={"name": "Updated Stop Name", "latitude": 13.3405},
            headers={"Authorization": "Bearer admin-token"},
        )
        assert r_patch.status_code == 200
        assert r_patch.json()["name"] == "Updated Stop Name"
        assert r_patch.json()["latitude"] == 13.3405

        # Deactivate
        r_del = await async_client.delete(
            f"/api/v1/boarding-points/{bp_id}",
            headers={"Authorization": "Bearer admin-token"},
        )
        assert r_del.status_code == 204

    # Verify is_active in DB
    async with async_session_factory() as session:
        refreshed = await session.get(BoardingPoint, uuid.UUID(bp_id))
        assert refreshed.is_active is False
