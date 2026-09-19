import uuid
from unittest.mock import patch
import pytest
from fastapi import HTTPException, status
from httpx import AsyncClient

from app.db.database import async_session_factory
from app.models.enums import UserRole
from app.models.user import User


async def create_test_user(role: UserRole, email_prefix: str = "user") -> User:
    """Helper to seed a test user with a specific role in PostgreSQL."""
    test_uid = f"fb-rbac-{role.value.lower()}-{uuid.uuid4().hex[:8]}"
    domain = "sode-edu.in" if role == UserRole.STUDENT else "test.invalid"
    test_email = f"{email_prefix}_{uuid.uuid4().hex[:8]}@{domain}"

    async with async_session_factory() as session:
        user = User(
            firebase_uid=test_uid,
            email=test_email,
            full_name=f"RBAC {role.value} User",
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


# --- CASE A & B: Unauthenticated & Malformed Token Tests ---

@pytest.mark.asyncio
async def test_rbac_admin_missing_token(async_client: AsyncClient):
    """CASE A: Request without Authorization header returns 401."""
    response = await async_client.get("/api/v1/rbac/admin-test")
    assert response.status_code == 401
    assert "Authorization header with Bearer token is required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_rbac_admin_invalid_token(async_client: AsyncClient):
    """CASE B: Request with invalid Firebase token returns 401."""
    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.side_effect = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )
        response = await async_client.get(
            "/api/v1/rbac/admin-test",
            headers={"Authorization": "Bearer bad-token"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid authentication token"


@pytest.mark.asyncio
async def test_rbac_unknown_user_in_database(async_client: AsyncClient):
    """Verified Firebase identity without DB user returns 404."""
    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {
            "uid": f"unregistered-{uuid.uuid4().hex[:8]}",
            "email": "unregistered@sode-edu.in",
        }
        response = await async_client.get(
            "/api/v1/rbac/admin-test",
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "User not found in system"


# --- CASE C & D: Admin Endpoint Authorization ---

@pytest.mark.asyncio
async def test_rbac_admin_accessing_admin_endpoint(async_client: AsyncClient):
    """CASE C: ADMIN accessing /admin-test returns 200."""
    admin = await create_test_user(UserRole.ADMIN, "admin")

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": admin.firebase_uid, "email": admin.email}
        response = await async_client.get(
            "/api/v1/rbac/admin-test",
            headers={"Authorization": "Bearer valid-admin-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Admin RBAC access granted"
        assert data["role"] == "ADMIN"
        assert data["user_id"] == str(admin.id)


@pytest.mark.asyncio
async def test_rbac_driver_accessing_admin_endpoint(async_client: AsyncClient):
    """CASE D: DRIVER accessing /admin-test returns 403 Forbidden."""
    driver = await create_test_user(UserRole.DRIVER, "driver")

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": driver.firebase_uid, "email": driver.email}
        response = await async_client.get(
            "/api/v1/rbac/admin-test",
            headers={"Authorization": "Bearer valid-driver-token"},
        )
        assert response.status_code == 403
        assert "Access forbidden" in response.json()["detail"]


# --- CASE E & F: Student & Parent Endpoints ---

@pytest.mark.asyncio
async def test_rbac_student_accessing_student_endpoint(async_client: AsyncClient):
    """CASE E: STUDENT accessing /student-test returns 200."""
    student = await create_test_user(UserRole.STUDENT, "student")

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": student.firebase_uid, "email": student.email}
        response = await async_client.get(
            "/api/v1/rbac/student-test",
            headers={"Authorization": "Bearer valid-student-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Student RBAC access granted"
        assert data["role"] == "STUDENT"


@pytest.mark.asyncio
async def test_rbac_parent_accessing_parent_endpoint(async_client: AsyncClient):
    """CASE F: PARENT accessing /parent-test returns 200."""
    parent = await create_test_user(UserRole.PARENT, "parent")

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": parent.firebase_uid, "email": parent.email}
        response = await async_client.get(
            "/api/v1/rbac/parent-test",
            headers={"Authorization": "Bearer valid-parent-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Parent RBAC access granted"
        assert data["role"] == "PARENT"


# --- Driver Endpoint Authorization ---

@pytest.mark.asyncio
async def test_rbac_driver_accessing_driver_endpoint(async_client: AsyncClient):
    """DRIVER accessing /driver-test returns 200."""
    driver = await create_test_user(UserRole.DRIVER, "driver")

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": driver.firebase_uid, "email": driver.email}
        response = await async_client.get(
            "/api/v1/rbac/driver-test",
            headers={"Authorization": "Bearer valid-driver-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Driver RBAC access granted"
        assert data["role"] == "DRIVER"


@pytest.mark.asyncio
async def test_rbac_student_accessing_driver_endpoint(async_client: AsyncClient):
    """STUDENT accessing /driver-test returns 403."""
    student = await create_test_user(UserRole.STUDENT, "student")

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": student.firebase_uid, "email": student.email}
        response = await async_client.get(
            "/api/v1/rbac/driver-test",
            headers={"Authorization": "Bearer valid-student-token"},
        )
        assert response.status_code == 403


# --- CASE G, H & I: Multi-role (Admin + Driver) Endpoint ---

@pytest.mark.asyncio
async def test_rbac_admin_accessing_admin_driver_endpoint(async_client: AsyncClient):
    """CASE G: ADMIN accessing /admin-driver-test returns 200."""
    admin = await create_test_user(UserRole.ADMIN, "admin")

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": admin.firebase_uid, "email": admin.email}
        response = await async_client.get(
            "/api/v1/rbac/admin-driver-test",
            headers={"Authorization": "Bearer valid-admin-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Admin/Driver RBAC access granted"
        assert data["role"] == "ADMIN"


@pytest.mark.asyncio
async def test_rbac_driver_accessing_admin_driver_endpoint(async_client: AsyncClient):
    """CASE H: DRIVER accessing /admin-driver-test returns 200."""
    driver = await create_test_user(UserRole.DRIVER, "driver")

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": driver.firebase_uid, "email": driver.email}
        response = await async_client.get(
            "/api/v1/rbac/admin-driver-test",
            headers={"Authorization": "Bearer valid-driver-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Admin/Driver RBAC access granted"
        assert data["role"] == "DRIVER"


@pytest.mark.asyncio
async def test_rbac_student_accessing_admin_driver_endpoint(async_client: AsyncClient):
    """CASE I: STUDENT accessing /admin-driver-test returns 403."""
    student = await create_test_user(UserRole.STUDENT, "student")

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": student.firebase_uid, "email": student.email}
        response = await async_client.get(
            "/api/v1/rbac/admin-driver-test",
            headers={"Authorization": "Bearer valid-student-token"},
        )
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_rbac_parent_accessing_admin_driver_endpoint(async_client: AsyncClient):
    """PARENT accessing /admin-driver-test returns 403."""
    parent = await create_test_user(UserRole.PARENT, "parent")

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": parent.firebase_uid, "email": parent.email}
        response = await async_client.get(
            "/api/v1/rbac/admin-driver-test",
            headers={"Authorization": "Bearer valid-parent-token"},
        )
        assert response.status_code == 403
