import uuid
from unittest.mock import patch
import pytest
from fastapi import HTTPException, status
from httpx import AsyncClient

from app.db.database import async_session_factory
from app.models.enums import UserRole
from app.models.user import User


@pytest.mark.asyncio
async def test_auth_me_missing_header(async_client: AsyncClient):
    """Calling /api/v1/auth/me without Authorization header returns 401."""
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "Authorization header with Bearer token is required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_auth_me_invalid_token(async_client: AsyncClient):
    """Calling /api/v1/auth/me with an invalid token returns 401."""
    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.side_effect = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )
        response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token-xyz"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid authentication token"


@pytest.mark.asyncio
async def test_auth_me_user_not_found(async_client: AsyncClient):
    """Verified Firebase identity without corresponding DB User returns 404."""
    non_existent_uid = f"fb-nonexistent-{uuid.uuid4().hex[:8]}"

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {
            "uid": non_existent_uid,
            "email": "ghost.user@sode-edu.in",
        }
        response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer valid-mock-token"},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "User not found in system"


@pytest.mark.asyncio
async def test_auth_me_success(async_client: AsyncClient):
    """Verified Firebase identity with existing DB User returns 200 and profile."""
    test_uid = f"fb-auth-{uuid.uuid4().hex[:8]}"
    test_email = f"auth.test_{uuid.uuid4().hex[:8]}@sode-edu.in"
    test_name = "Auth Verified Student"

    # Seed user in DB
    async with async_session_factory() as session:
        user = User(
            firebase_uid=test_uid,
            email=test_email,
            full_name=test_name,
            role=UserRole.STUDENT,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = str(user.id)

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {
            "uid": test_uid,
            "email": test_email,
        }
        response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer valid-mock-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert data["firebase_uid"] == test_uid
        assert data["email"] == test_email
        assert data["full_name"] == test_name
        assert data["role"] == "STUDENT"
        assert "created_at" in data
        assert "updated_at" in data
