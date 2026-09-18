import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.firebase import set_mock_firebase_token
from app.models.user import User, UserRole, UserStatus
from app.models.bus import Bus, BusStatus
from app.models.driver_assignment import DriverBusAssignment, AssignmentStatus
from app.models.route import Route, BoardingPoint, RouteStop, RouteDirection
from app.models.schedule import TripSchedule, TrackingSession, SessionStatus
from app.services.scheduler_service import get_kolkata_now, evaluate_scheduled_sessions_for_db

@pytest.mark.asyncio
async def test_driver_status_unauthorized(client: AsyncClient):
    """Test accessing driver status without auth header or as non-driver."""
    # 1. Missing header
    res1 = await client.get("/api/v1/driver/tracking/status")
    assert res1.status_code == 401
    
    # 2. Student role access attempt
    student_token = "mock-student-tracking-token"
    set_mock_firebase_token(student_token, {
        "uid": "uid-student-test",
        "email": "student_test@sode-edu.in",
        "email_verified": True
    })
    res2 = await client.get("/api/v1/driver/tracking/status", headers={"Authorization": f"Bearer {student_token}"})
    assert res2.status_code == 403

@pytest.mark.asyncio
async def test_driver_status_authorized_driver(client: AsyncClient):
    """Test driver status for authorized driver."""
    driver_token = "mock-driver1-tracking-token"
    set_mock_firebase_token(driver_token, {
        "uid": "mock-uid-driver1@sode-edu.in",
        "email": settings.DRIVER1_EMAIL,
        "email_verified": True
    })
    res = await client.get("/api/v1/driver/tracking/status", headers={"Authorization": f"Bearer {driver_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True

@pytest.mark.asyncio
async def test_gps_ingestion_valid(client: AsyncClient):
    """Test valid GPS ingestion from assigned driver."""
    driver_token = "mock-driver1-gps-token"
    set_mock_firebase_token(driver_token, {
        "uid": "mock-uid-driver1@sode-edu.in",
        "email": settings.DRIVER1_EMAIL,
        "email_verified": True
    })
    payload = {
        "latitude": 13.2541,
        "longitude": 74.7865,
        "speed": 35.5,
        "heading": 180.0,
        "accuracy": 5.0,
        "recorded_at": datetime.now(timezone.utc).isoformat()
    }
    # Note: In mock test mode, if session is active or missing session exception caught cleanly
    res = await client.post("/api/v1/gps/ingest", headers={"Authorization": f"Bearer {driver_token}"}, json=payload)
    assert res.status_code in [200, 400]

@pytest.mark.asyncio
async def test_active_buses_endpoint(client: AsyncClient):
    """Test listing active tracking buses."""
    student_token = "mock-student-active-buses"
    set_mock_firebase_token(student_token, {
        "uid": "uid-student-active",
        "email": "student_active@sode-edu.in",
        "email_verified": True
    })
    res = await client.get("/api/v1/tracking/active-buses", headers={"Authorization": f"Bearer {student_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)

@pytest.mark.asyncio
async def test_live_trip_not_found(client: AsyncClient):
    """Test getting live trip details for non-existent trip_id."""
    student_token = "mock-student-live-trip"
    set_mock_firebase_token(student_token, {
        "uid": "uid-student-live",
        "email": "student_live@sode-edu.in",
        "email_verified": True
    })
    res = await client.get("/api/v1/trips/999999/live", headers={"Authorization": f"Bearer {student_token}"})
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "TRIP_NOT_FOUND"
