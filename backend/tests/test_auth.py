import pytest
from httpx import AsyncClient
from app.core.config import settings
from app.core.firebase import set_mock_firebase_token
from scripts.seed_auth_users import seed_users

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_missing_auth_header(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "MISSING_AUTHENTICATION_TOKEN"

@pytest.mark.asyncio
async def test_invalid_auth_token(client: AsyncClient):
    headers = {"Authorization": "Bearer invalid_garbage_token"}
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_OR_EXPIRED_TOKEN"

@pytest.mark.asyncio
async def test_student_valid_domain_signup(client: AsyncClient):
    token = "token-student-valid"
    email = "student1@sode-edu.in"
    set_mock_firebase_token(token, {"uid": "uid_student1", "email": email, "email_verified": True})
    
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post("/api/v1/auth/sync-user", headers=headers, json={})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["user"]["email"] == email
    assert data["data"]["user"]["role"] == "STUDENT"

@pytest.mark.asyncio
async def test_student_gmail_domain_rejected(client: AsyncClient):
    token = "token-student-gmail"
    email = "student@gmail.com"
    set_mock_firebase_token(token, {"uid": "uid_gmail", "email": email, "email_verified": True})
    
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post("/api/v1/auth/sync-user", headers=headers, json={})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "STUDENT_EMAIL_DOMAIN_NOT_ALLOWED"

@pytest.mark.asyncio
async def test_student_yahoo_domain_rejected(client: AsyncClient):
    token = "token-student-yahoo"
    email = "student@yahoo.com"
    set_mock_firebase_token(token, {"uid": "uid_yahoo", "email": email, "email_verified": True})
    
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post("/api/v1/auth/sync-user", headers=headers, json={})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "STUDENT_EMAIL_DOMAIN_NOT_ALLOWED"

@pytest.mark.asyncio
async def test_student_fake_suffix_domain_rejected(client: AsyncClient):
    token = "token-student-fake"
    email = "student@sode-edu.in.fake.com"
    set_mock_firebase_token(token, {"uid": "uid_fake", "email": email, "email_verified": True})
    
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post("/api/v1/auth/sync-user", headers=headers, json={})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "STUDENT_EMAIL_DOMAIN_NOT_ALLOWED"

@pytest.mark.asyncio
async def test_role_tampering_attempt_ignored(client: AsyncClient):
    token = "token-student-tamper"
    email = "sagar@sode-edu.in"
    set_mock_firebase_token(token, {"uid": "uid_tamper", "email": email, "email_verified": True})
    
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post("/api/v1/auth/sync-user", headers=headers, json={"role": "ADMIN"})
    assert response.status_code == 200
    user = response.json()["data"]["user"]
    assert user["role"] == "STUDENT"  # Must remain STUDENT

@pytest.mark.asyncio
async def test_admin_auth_and_guard(client: AsyncClient):
    admin_email = settings.ADMIN1_EMAIL
    token = "token-admin1"
    set_mock_firebase_token(token, {"uid": "seeded_uid_admin1", "email": admin_email, "email_verified": True})
    
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    user = response.json()["data"]["user"]
    assert user["email"] == admin_email
    assert user["role"] == "ADMIN"
    
    response_guard = await client.get("/api/v1/auth/admin-only", headers=headers)
    assert response_guard.status_code == 200

@pytest.mark.asyncio
async def test_driver_auth_and_guard(client: AsyncClient):
    driver_email = settings.DRIVER1_EMAIL
    token = "token-driver1"
    set_mock_firebase_token(token, {"uid": "seeded_uid_driver1", "email": driver_email, "email_verified": True})
    
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    user = response.json()["data"]["user"]
    assert user["email"] == driver_email
    assert user["role"] == "DRIVER"
    
    response_driver = await client.get("/api/v1/auth/driver-only", headers=headers)
    assert response_driver.status_code == 200
    
    response_admin = await client.get("/api/v1/auth/admin-only", headers=headers)
    assert response_admin.status_code == 403
    assert response_admin.json()["error"]["code"] == "INSUFFICIENT_PERMISSIONS"

@pytest.mark.asyncio
async def test_student_accessing_admin_and_driver_endpoints_rejected(client: AsyncClient):
    token = "token-student-access"
    email = "student2@sode-edu.in"
    set_mock_firebase_token(token, {"uid": "uid_student2", "email": email, "email_verified": True})
    headers = {"Authorization": f"Bearer {token}"}
    
    resp_student = await client.get("/api/v1/auth/student-only", headers=headers)
    assert resp_student.status_code == 200
    
    resp_admin = await client.get("/api/v1/auth/admin-only", headers=headers)
    assert resp_admin.status_code == 403
    assert resp_admin.json()["error"]["code"] == "INSUFFICIENT_PERMISSIONS"
    
    resp_driver = await client.get("/api/v1/auth/driver-only", headers=headers)
    assert resp_driver.status_code == 403
    assert resp_driver.json()["error"]["code"] == "INSUFFICIENT_PERMISSIONS"

@pytest.mark.asyncio
async def test_logout_endpoint(client: AsyncClient):
    token = "token-logout"
    email = "student3@sode-edu.in"
    set_mock_firebase_token(token, {"uid": "uid_logout", "email": email, "email_verified": True})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await client.post("/api/v1/auth/logout", headers=headers)
    assert response.status_code == 200
    assert response.json()["success"] is True

@pytest.mark.asyncio
async def test_seed_script_execution():
    seed_users()
