import uuid
from unittest.mock import patch
import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from httpx import AsyncClient

from app.db.database import async_session_factory
from app.models.enums import UserRole
from app.models.route import Route
from app.models.user import User
from app.schemas.route import RouteCreate, RouteUpdate


async def create_test_user(role: UserRole, prefix: str = "user") -> User:
    """Helper to seed a test user with a specific role."""
    test_uid = f"fb-route-{role.value.lower()}-{uuid.uuid4().hex[:8]}"
    domain = "sode-edu.in" if role == UserRole.STUDENT else "test.invalid"
    test_email = f"{prefix}_{uuid.uuid4().hex[:8]}@{domain}"

    async with async_session_factory() as session:
        user = User(
            firebase_uid=test_uid,
            email=test_email,
            full_name=f"Route Test {role.value}",
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


# --- 1. MODEL & SCHEMA VALIDATION TESTS ---

@pytest.mark.asyncio
async def test_route_model_creation_and_defaults():
    """Verify Route model creates with expected fields and defaults."""
    code = f"R-{uuid.uuid4().hex[:6].upper()}"
    async with async_session_factory() as session:
        route = Route(name="Campus Express", code=code, description="Main Campus Line")
        session.add(route)
        await session.commit()
        await session.refresh(route)

        assert route.id is not None
        assert route.name == "Campus Express"
        assert route.code == code
        assert route.is_active is True
        assert route.created_at is not None
        assert route.updated_at is not None


@pytest.mark.asyncio
async def test_route_code_unique_constraint():
    """Duplicate route code must raise IntegrityError."""
    code = f"R-{uuid.uuid4().hex[:6].upper()}"
    async with async_session_factory() as session:
        r1 = Route(name="Route 1", code=code)
        session.add(r1)
        await session.commit()

    async with async_session_factory() as session:
        r2 = Route(name="Route 2", code=code)
        session.add(r2)
        with pytest.raises(IntegrityError):
            await session.commit()


def test_route_schema_validation():
    """Blank or whitespace route name/code must be rejected."""
    with pytest.raises(ValidationError):
        RouteCreate(name="   ", code="R-01")

    with pytest.raises(ValidationError):
        RouteCreate(name="Route", code="")


# --- 2. API CRUD & RBAC TESTS ---

@pytest.mark.asyncio
async def test_create_route_admin_success(async_client: AsyncClient):
    """ADMIN can create a new route (201 Created)."""
    admin = await create_test_user(UserRole.ADMIN, "admin_route_create")
    code = f"R-{uuid.uuid4().hex[:6].upper()}"

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": admin.firebase_uid, "email": admin.email}
        response = await async_client.post(
            "/api/v1/routes",
            json={"name": "North Campus Loop", "code": code, "description": "North gate stops"},
            headers={"Authorization": "Bearer admin-token"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "North Campus Loop"
        assert data["code"] == code
        assert data["is_active"] is True
        assert "id" in data


@pytest.mark.asyncio
async def test_create_route_non_admin_forbidden(async_client: AsyncClient):
    """Non-admin roles cannot create routes (403 Forbidden)."""
    for role in [UserRole.DRIVER, UserRole.STUDENT, UserRole.PARENT]:
        user = await create_test_user(role, f"route_user_{role.value.lower()}")
        with patch("app.core.security.verify_firebase_token") as mock_verify:
            mock_verify.return_value = {"uid": user.firebase_uid, "email": user.email}
            response = await async_client.post(
                "/api/v1/routes",
                json={"name": "Forbidden Route", "code": f"R-{uuid.uuid4().hex[:6]}"},
                headers={"Authorization": "Bearer user-token"},
            )
            assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_route_duplicate_code_rejected(async_client: AsyncClient):
    """Duplicate route code returns 409 Conflict."""
    admin = await create_test_user(UserRole.ADMIN, "admin_route_dup")
    code = f"R-{uuid.uuid4().hex[:6].upper()}"

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": admin.firebase_uid, "email": admin.email}
        # First creation
        r1 = await async_client.post(
            "/api/v1/routes",
            json={"name": "Route A", "code": code},
            headers={"Authorization": "Bearer admin-token"},
        )
        assert r1.status_code == 201

        # Duplicate
        r2 = await async_client.post(
            "/api/v1/routes",
            json={"name": "Route B", "code": code},
            headers={"Authorization": "Bearer admin-token"},
        )
        assert r2.status_code == 409
        assert "already exists" in r2.json()["detail"]


@pytest.mark.asyncio
async def test_list_and_get_routes(async_client: AsyncClient):
    """ADMIN can list routes and get route by ID (200 OK)."""
    admin = await create_test_user(UserRole.ADMIN, "admin_route_read")
    code = f"R-{uuid.uuid4().hex[:6].upper()}"

    async with async_session_factory() as session:
        route = Route(name="South Campus", code=code)
        session.add(route)
        await session.commit()
        await session.refresh(route)
        route_id = str(route.id)

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": admin.firebase_uid, "email": admin.email}

        # List
        r_list = await async_client.get("/api/v1/routes", headers={"Authorization": "Bearer admin-token"})
        assert r_list.status_code == 200
        assert any(r["id"] == route_id for r in r_list.json())

        # Get by ID
        r_get = await async_client.get(f"/api/v1/routes/{route_id}", headers={"Authorization": "Bearer admin-token"})
        assert r_get.status_code == 200
        assert r_get.json()["code"] == code


@pytest.mark.asyncio
async def test_update_and_deactivate_route(async_client: AsyncClient):
    """ADMIN can update route attributes and safely deactivate."""
    admin = await create_test_user(UserRole.ADMIN, "admin_route_update")
    code = f"R-{uuid.uuid4().hex[:6].upper()}"

    async with async_session_factory() as session:
        route = Route(name="Old Name", code=code)
        session.add(route)
        await session.commit()
        await session.refresh(route)
        route_id = str(route.id)

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": admin.firebase_uid, "email": admin.email}

        # Update
        r_patch = await async_client.patch(
            f"/api/v1/routes/{route_id}",
            json={"name": "New Name", "description": "Updated description"},
            headers={"Authorization": "Bearer admin-token"},
        )
        assert r_patch.status_code == 200
        assert r_patch.json()["name"] == "New Name"

        # Deactivate
        r_del = await async_client.delete(
            f"/api/v1/routes/{route_id}",
            headers={"Authorization": "Bearer admin-token"},
        )
        assert r_del.status_code == 204

    # Verify is_active in DB
    async with async_session_factory() as session:
        refreshed = await session.get(Route, uuid.UUID(route_id))
        assert refreshed.is_active is False
