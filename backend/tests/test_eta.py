import json
import uuid
from datetime import datetime, timezone
from unittest.mock import patch
import pytest
from httpx import AsyncClient

from app.core.config import Settings, settings
from app.db.database import async_session_factory
from app.models.boarding_point import BoardingPoint
from app.models.bus import Bus
from app.models.enums import ParentLinkStatus, TripStatus, UserRole
from app.models.parent_child import ParentChildren, ParentLinkRequest
from app.models.route import Route
from app.models.route_stop import RouteStop
from app.models.trip import Trip
from app.models.user import User
from app.services.gps_service import get_live_location_key


def mock_firebase_verify(mock_uid: str, mock_email: str):
    return patch(
        "app.core.security.verify_firebase_token",
        return_value={
            "uid": mock_uid,
            "email": mock_email,
            "name": "Test User",
        },
    )


async def setup_eta_test_data() -> dict:
    """Helper to seed users, buses, route, boarding points, stops, and trips for ETA tests."""
    async with async_session_factory() as db:
        uid = uuid.uuid4().hex[:8]

        # 1. Create Users (Admin, Driver 1, Driver 2, Student, Parent, Unlinked Parent)
        admin = User(
            firebase_uid=f"firebase_admin_{uid}",
            email=f"admin_{uid}@sode.edu.in",
            full_name="Admin User",
            role=UserRole.ADMIN,
        )
        driver1 = User(
            firebase_uid=f"firebase_driver1_{uid}",
            email=f"driver1_{uid}@sode.edu.in",
            full_name="Driver One",
            role=UserRole.DRIVER,
        )
        driver2 = User(
            firebase_uid=f"firebase_driver2_{uid}",
            email=f"driver2_{uid}@sode.edu.in",
            full_name="Driver Two",
            role=UserRole.DRIVER,
        )
        student = User(
            firebase_uid=f"firebase_student_{uid}",
            email=f"student_{uid}@sode.edu.in",
            full_name="Student User",
            role=UserRole.STUDENT,
        )
        parent_approved = User(
            firebase_uid=f"firebase_parent_appr_{uid}",
            email=f"parent_appr_{uid}@example.com",
            full_name="Approved Parent",
            role=UserRole.PARENT,
        )
        parent_unapproved = User(
            firebase_uid=f"firebase_parent_unappr_{uid}",
            email=f"parent_unappr_{uid}@example.com",
            full_name="Unapproved Parent",
            role=UserRole.PARENT,
        )
        db.add_all([admin, driver1, driver2, student, parent_approved, parent_unapproved])
        await db.flush()

        # 2. Create Buses
        bus1 = Bus(
            registration_number=f"KA-20-ETA-{uid[:4]}A",
            bus_number=f"B-ETA-1-{uid[:4]}",
            capacity=40,
            is_active=True,
        )
        bus2 = Bus(
            registration_number=f"KA-20-ETA-{uid[:4]}B",
            bus_number=f"B-ETA-2-{uid[:4]}",
            capacity=40,
            is_active=True,
        )
        db.add_all([bus1, bus2])
        await db.flush()

        # Assign bus1 to driver1 and student, bus2 to driver2
        driver1.assigned_bus_id = bus1.id
        student.assigned_bus_id = bus1.id
        driver2.assigned_bus_id = bus2.id
        await db.flush()

        # 3. Create Parent-Child links
        # Approved link
        pc_approved = ParentChildren(
            parent_id=parent_approved.id,
            student_id=student.id,
        )
        # Pending link (unapproved)
        req_pending = ParentLinkRequest(
            parent_id=parent_unapproved.id,
            student_id=student.id,
            status=ParentLinkStatus.PENDING,
        )
        db.add_all([pc_approved, req_pending])

        # 4. Create Route & Boarding Points
        route = Route(
            name=f"Campus Express {uid}",
            code=f"R-ETA-{uid}",
            description="Route for ETA testing",
            is_active=True,
        )
        db.add(route)
        await db.flush()

        # Point 1: MIT Main Gate (lat: 13.34088, lon: 74.74214)
        # Point 2: Tiger Circle (lat: 13.35240, lon: 74.78650) (~4.97 km)
        # Point 3: Syndicate Circle (lat: 13.36000, lon: 74.79500) (~6.0 km)
        bp1 = BoardingPoint(
            name="MIT Main Gate",
            latitude=13.34088,
            longitude=74.74214,
            is_active=True,
        )
        bp2 = BoardingPoint(
            name="Tiger Circle",
            latitude=13.35240,
            longitude=74.78650,
            is_active=True,
        )
        bp3 = BoardingPoint(
            name="Syndicate Circle",
            latitude=13.36000,
            longitude=74.79500,
            is_active=True,
        )
        db.add_all([bp1, bp2, bp3])
        await db.flush()

        # Route stops in order
        rs1 = RouteStop(route_id=route.id, boarding_point_id=bp1.id, stop_order=1)
        rs2 = RouteStop(route_id=route.id, boarding_point_id=bp2.id, stop_order=2)
        rs3 = RouteStop(route_id=route.id, boarding_point_id=bp3.id, stop_order=3)
        db.add_all([rs1, rs2, rs3])
        await db.flush()

        # 5. Create Trips
        trip_active = Trip(
            route_id=route.id,
            bus_id=bus1.id,
            driver_id=driver1.id,
            status=TripStatus.IN_PROGRESS,
        )
        trip_scheduled = Trip(
            route_id=route.id,
            bus_id=bus1.id,
            driver_id=driver1.id,
            status=TripStatus.SCHEDULED,
        )
        trip_completed = Trip(
            route_id=route.id,
            bus_id=bus1.id,
            driver_id=driver1.id,
            status=TripStatus.COMPLETED,
        )
        trip_cancelled = Trip(
            route_id=route.id,
            bus_id=bus1.id,
            driver_id=driver1.id,
            status=TripStatus.CANCELLED,
        )
        trip_other = Trip(
            route_id=route.id,
            bus_id=bus2.id,
            driver_id=driver2.id,
            status=TripStatus.IN_PROGRESS,
        )
        db.add_all([trip_active, trip_scheduled, trip_completed, trip_cancelled, trip_other])
        await db.commit()

        return {
            "admin": admin,
            "driver1": driver1,
            "driver2": driver2,
            "student": student,
            "parent_approved": parent_approved,
            "parent_unapproved": parent_unapproved,
            "bus1": bus1,
            "bus2": bus2,
            "route": route,
            "bp1": bp1,
            "bp2": bp2,
            "bp3": bp3,
            "trip_active": trip_active,
            "trip_scheduled": trip_scheduled,
            "trip_completed": trip_completed,
            "trip_cancelled": trip_cancelled,
            "trip_other": trip_other,
        }


@pytest.mark.asyncio
async def test_eta_success_admin_and_fields(async_client: AsyncClient, fake_redis):
    """Admin receives a complete, deterministic ETA response for an in-progress trip with live Redis data."""
    env = await setup_eta_test_data()
    trip = env["trip_active"]
    admin = env["admin"]

    # Seed live location in Redis near Stop 1 (lat: 13.34090, lon: 74.74220) (~6.87m away)
    recorded_at = datetime.now(timezone.utc)
    live_payload = {
        "trip_id": str(trip.id),
        "driver_id": str(env["driver1"].id),
        "bus_id": str(env["bus1"].id),
        "latitude": 13.34090,
        "longitude": 74.74220,
        "recorded_at": recorded_at.isoformat(),
        "received_at": recorded_at.isoformat(),
        "recorded_at_epoch": recorded_at.timestamp(),
    }
    await fake_redis.set(get_live_location_key(trip.id), json.dumps(live_payload))

    with mock_firebase_verify(admin.firebase_uid, admin.email):
        response = await async_client.get(
            f"/api/v1/trips/{trip.id}/eta",
            headers={"Authorization": "Bearer mock_admin_token"},
        )

    assert response.status_code == 200
    data = response.json()

    assert data["trip_id"] == str(trip.id)
    assert data["current_latitude"] == 13.34090
    assert data["current_longitude"] == 74.74220
    assert "generated_at" in data

    # 3 stops must be returned in strict stop_order ascending
    stops = data["stops"]
    assert len(stops) == 3
    assert stops[0]["stop_order"] == 1
    assert stops[1]["stop_order"] == 2
    assert stops[2]["stop_order"] == 3

    # Stop 1 is ~6.87m away
    assert 5.0 <= stops[0]["distance_meters"] <= 10.0
    # At 8.0 m/s, eta_seconds ~ 6.87 / 8.0 ~ 0.9s
    assert 0.5 <= stops[0]["eta_seconds"] <= 2.0
    assert stops[0]["boarding_point_name"] == "MIT Main Gate"

    # Stop 2 (Tiger Circle) is ~4.97km away
    assert 4800.0 <= stops[1]["distance_meters"] <= 5200.0
    assert 600.0 <= stops[1]["eta_seconds"] <= 650.0

    # Stop 3 is further than Stop 2
    assert stops[2]["distance_meters"] > stops[1]["distance_meters"]
    assert stops[2]["eta_seconds"] > stops[1]["eta_seconds"]

    # Timestamps must be valid ISO8601 UTC
    for s in stops:
        arr_dt = datetime.fromisoformat(s["estimated_arrival_at"])
        assert arr_dt.tzinfo is not None


@pytest.mark.asyncio
async def test_eta_driver_can_access_own_trip(async_client: AsyncClient, fake_redis):
    """Driver can successfully retrieve ETA for their own assigned trip."""
    env = await setup_eta_test_data()
    trip = env["trip_active"]
    driver = env["driver1"]

    recorded_at = datetime.now(timezone.utc)
    live_payload = {
        "trip_id": str(trip.id),
        "driver_id": str(driver.id),
        "bus_id": str(env["bus1"].id),
        "latitude": 13.34090,
        "longitude": 74.74220,
        "recorded_at": recorded_at.isoformat(),
        "received_at": recorded_at.isoformat(),
    }
    await fake_redis.set(get_live_location_key(trip.id), json.dumps(live_payload))

    with mock_firebase_verify(driver.firebase_uid, driver.email):
        response = await async_client.get(
            f"/api/v1/trips/{trip.id}/eta",
            headers={"Authorization": "Bearer mock_driver_token"},
        )

    assert response.status_code == 200
    assert response.json()["trip_id"] == str(trip.id)


@pytest.mark.asyncio
async def test_eta_driver_forbidden_from_other_driver_trip(async_client: AsyncClient, fake_redis):
    """Driver is rejected with 403 Forbidden when requesting ETA for another driver's trip."""
    env = await setup_eta_test_data()
    trip = env["trip_other"]  # Driver 2's trip
    driver1 = env["driver1"]

    with mock_firebase_verify(driver1.firebase_uid, driver1.email):
        response = await async_client.get(
            f"/api/v1/trips/{trip.id}/eta",
            headers={"Authorization": "Bearer mock_driver1_token"},
        )

    assert response.status_code == 403
    assert "own assigned trips" in response.json()["detail"]


@pytest.mark.asyncio
async def test_eta_approved_parent_access_success(async_client: AsyncClient, fake_redis):
    """Parent with an approved student link can access ETA for the child's active bus trip."""
    env = await setup_eta_test_data()
    trip = env["trip_active"]
    parent = env["parent_approved"]

    recorded_at = datetime.now(timezone.utc)
    live_payload = {
        "trip_id": str(trip.id),
        "driver_id": str(env["driver1"].id),
        "bus_id": str(env["bus1"].id),
        "latitude": 13.34090,
        "longitude": 74.74220,
        "recorded_at": recorded_at.isoformat(),
        "received_at": recorded_at.isoformat(),
    }
    await fake_redis.set(get_live_location_key(trip.id), json.dumps(live_payload))

    with mock_firebase_verify(parent.firebase_uid, parent.email):
        response = await async_client.get(
            f"/api/v1/trips/{trip.id}/eta",
            headers={"Authorization": "Bearer mock_parent_token"},
        )

    assert response.status_code == 200
    assert response.json()["trip_id"] == str(trip.id)


@pytest.mark.asyncio
async def test_eta_unapproved_parent_forbidden(async_client: AsyncClient, fake_redis):
    """Parent without an approved relationship is rejected with 403 Forbidden."""
    env = await setup_eta_test_data()
    trip = env["trip_active"]
    parent_unapproved = env["parent_unapproved"]

    with mock_firebase_verify(parent_unapproved.firebase_uid, parent_unapproved.email):
        response = await async_client.get(
            f"/api/v1/trips/{trip.id}/eta",
            headers={"Authorization": "Bearer mock_unappr_token"},
        )

    assert response.status_code == 403
    assert "approved child assigned" in response.json()["detail"]


@pytest.mark.asyncio
async def test_eta_student_access_rules(async_client: AsyncClient, fake_redis):
    """Student can access ETA for their assigned bus trip, but is rejected for unrelated trips."""
    env = await setup_eta_test_data()
    trip_active = env["trip_active"]  # bus1 (assigned to student)
    trip_other = env["trip_other"]    # bus2 (not assigned to student)
    student = env["student"]

    # Seed live location for active trip
    recorded_at = datetime.now(timezone.utc)
    live_payload = {
        "trip_id": str(trip_active.id),
        "driver_id": str(env["driver1"].id),
        "bus_id": str(env["bus1"].id),
        "latitude": 13.34090,
        "longitude": 74.74220,
        "recorded_at": recorded_at.isoformat(),
        "received_at": recorded_at.isoformat(),
    }
    await fake_redis.set(get_live_location_key(trip_active.id), json.dumps(live_payload))

    # Assigned bus trip -> 200 OK
    with mock_firebase_verify(student.firebase_uid, student.email):
        res_ok = await async_client.get(
            f"/api/v1/trips/{trip_active.id}/eta",
            headers={"Authorization": "Bearer mock_student_token"},
        )
    assert res_ok.status_code == 200

    # Unassigned bus trip -> 403 Forbidden
    with mock_firebase_verify(student.firebase_uid, student.email):
        res_forbid = await async_client.get(
            f"/api/v1/trips/{trip_other.id}/eta",
            headers={"Authorization": "Bearer mock_student_token"},
        )
    assert res_forbid.status_code == 403


@pytest.mark.asyncio
async def test_eta_missing_live_location_returns_404(async_client: AsyncClient, fake_redis):
    """If no live location exists in Redis for an in-progress trip, endpoint returns 404 Not Found."""
    env = await setup_eta_test_data()
    trip = env["trip_active"]
    admin = env["admin"]

    await fake_redis.delete(get_live_location_key(trip.id))

    with mock_firebase_verify(admin.firebase_uid, admin.email):
        response = await async_client.get(
            f"/api/v1/trips/{trip.id}/eta",
            headers={"Authorization": "Bearer mock_admin_token"},
        )

    assert response.status_code == 404
    assert "No live location available" in response.json()["detail"]


@pytest.mark.asyncio
async def test_eta_scheduled_trip_returns_409(async_client: AsyncClient, fake_redis):
    """ETA requested on a SCHEDULED trip returns 409 Conflict."""
    env = await setup_eta_test_data()
    trip = env["trip_scheduled"]
    admin = env["admin"]

    with mock_firebase_verify(admin.firebase_uid, admin.email):
        response = await async_client.get(
            f"/api/v1/trips/{trip.id}/eta",
            headers={"Authorization": "Bearer mock_admin_token"},
        )

    assert response.status_code == 409
    assert "Trip must be IN_PROGRESS" in response.json()["detail"]


@pytest.mark.asyncio
async def test_eta_completed_trip_returns_409(async_client: AsyncClient, fake_redis):
    """ETA requested on a COMPLETED trip returns 409 Conflict."""
    env = await setup_eta_test_data()
    trip = env["trip_completed"]
    admin = env["admin"]

    with mock_firebase_verify(admin.firebase_uid, admin.email):
        response = await async_client.get(
            f"/api/v1/trips/{trip.id}/eta",
            headers={"Authorization": "Bearer mock_admin_token"},
        )

    assert response.status_code == 409
    assert "Trip must be IN_PROGRESS" in response.json()["detail"]


@pytest.mark.asyncio
async def test_eta_cancelled_trip_returns_409(async_client: AsyncClient, fake_redis):
    """ETA requested on a CANCELLED trip returns 409 Conflict."""
    env = await setup_eta_test_data()
    trip = env["trip_cancelled"]
    admin = env["admin"]

    with mock_firebase_verify(admin.firebase_uid, admin.email):
        response = await async_client.get(
            f"/api/v1/trips/{trip.id}/eta",
            headers={"Authorization": "Bearer mock_admin_token"},
        )

    assert response.status_code == 409
    assert "Trip must be IN_PROGRESS" in response.json()["detail"]


@pytest.mark.asyncio
async def test_eta_nonexistent_trip_returns_404(async_client: AsyncClient):
    """Requesting ETA for a nonexistent trip ID returns 404 Not Found."""
    env = await setup_eta_test_data()
    admin = env["admin"]
    random_id = uuid.uuid4()

    with mock_firebase_verify(admin.firebase_uid, admin.email):
        response = await async_client.get(
            f"/api/v1/trips/{random_id}/eta",
            headers={"Authorization": "Bearer mock_admin_token"},
        )

    assert response.status_code == 404
    assert "Trip not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_eta_redis_failure_returns_503(async_client: AsyncClient, fake_redis):
    """Redis outage during ETA query returns 503 Service Unavailable."""
    env = await setup_eta_test_data()
    trip = env["trip_active"]
    admin = env["admin"]

    fake_redis.is_healthy = False

    with mock_firebase_verify(admin.firebase_uid, admin.email):
        response = await async_client.get(
            f"/api/v1/trips/{trip.id}/eta",
            headers={"Authorization": "Bearer mock_admin_token"},
        )

    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"]


@pytest.mark.asyncio
async def test_eta_unauthenticated_requests_rejected(async_client: AsyncClient):
    """Missing or invalid auth tokens return 401 Unauthorized."""
    env = await setup_eta_test_data()
    trip = env["trip_active"]

    # Missing token
    res_missing = await async_client.get(f"/api/v1/trips/{trip.id}/eta")
    assert res_missing.status_code == 401

    # Invalid token
    res_invalid = await async_client.get(
        f"/api/v1/trips/{trip.id}/eta",
        headers={"Authorization": "Bearer invalid_token"},
    )
    assert res_invalid.status_code == 401


@pytest.mark.asyncio
async def test_eta_zero_distance_handling(async_client: AsyncClient, fake_redis):
    """When the bus is at the exact coordinates of a stop, distance and eta_seconds are 0.0."""
    env = await setup_eta_test_data()
    trip = env["trip_active"]
    admin = env["admin"]
    bp1 = env["bp1"]

    recorded_at = datetime.now(timezone.utc)
    live_payload = {
        "trip_id": str(trip.id),
        "driver_id": str(env["driver1"].id),
        "bus_id": str(env["bus1"].id),
        "latitude": bp1.latitude,
        "longitude": bp1.longitude,
        "recorded_at": recorded_at.isoformat(),
        "received_at": recorded_at.isoformat(),
    }
    await fake_redis.set(get_live_location_key(trip.id), json.dumps(live_payload))

    with mock_firebase_verify(admin.firebase_uid, admin.email):
        response = await async_client.get(
            f"/api/v1/trips/{trip.id}/eta",
            headers={"Authorization": "Bearer mock_admin_token"},
        )

    assert response.status_code == 200
    stops = response.json()["stops"]
    assert stops[0]["distance_meters"] == 0.0
    assert stops[0]["eta_seconds"] == 0.0


def test_eta_speed_configuration_validation():
    """Settings validator rejects zero or negative DEFAULT_ETA_SPEED_MPS."""
    s = Settings(DEFAULT_ETA_SPEED_MPS=10.0)
    assert s.DEFAULT_ETA_SPEED_MPS == 10.0

    with pytest.raises(ValueError, match="strictly greater than 0"):
        Settings(DEFAULT_ETA_SPEED_MPS=0.0)

    with pytest.raises(ValueError, match="strictly greater than 0"):
        Settings(DEFAULT_ETA_SPEED_MPS=-5.0)
