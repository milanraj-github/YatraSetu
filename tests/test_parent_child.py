import uuid
from datetime import datetime, timezone
from unittest.mock import patch
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db.database import async_session_factory
from app.models.bus import Bus
from app.models.enums import ParentLinkStatus, TripStatus, UserRole
from app.models.parent_child import ParentChildren, ParentLinkRequest
from app.models.route import Route
from app.models.trip import Trip
from app.models.user import User
from app.services.gps_service import update_trip_live_location


async def create_test_user(
    role: UserRole,
    prefix: str = "pc_user",
    assigned_bus_id: uuid.UUID | None = None,
) -> User:
    """Helper to seed a test user with a specific role and optional assigned bus."""
    test_uid = f"fb-pc-{role.value.lower()}-{uuid.uuid4().hex[:8]}"
    domain = "sode-edu.in" if role == UserRole.STUDENT else "example.com"
    test_email = f"{prefix}_{uuid.uuid4().hex[:8]}@{domain}"

    async with async_session_factory() as session:
        user = User(
            firebase_uid=test_uid,
            email=test_email,
            full_name=f"PC Test {role.value}",
            role=role,
            assigned_bus_id=assigned_bus_id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def create_test_bus() -> Bus:
    """Helper to seed a test bus."""
    bus_num = f"BUS-PC-{uuid.uuid4().hex[:6].upper()}"
    reg_num = f"KA-20-PC-{uuid.uuid4().hex[:4].upper()}"

    async with async_session_factory() as session:
        bus = Bus(
            bus_number=bus_num,
            registration_number=reg_num,
            capacity=40,
            is_active=True,
        )
        session.add(bus)
        await session.commit()
        await session.refresh(bus)
        return bus


async def create_test_route() -> Route:
    """Helper to seed a test route."""
    code = f"RPC-{uuid.uuid4().hex[:6].upper()}"
    async with async_session_factory() as session:
        route = Route(name="Campus Parent Route", code=code, is_active=True)
        session.add(route)
        await session.commit()
        await session.refresh(route)
        return route


async def create_test_trip(
    driver: User,
    bus: Bus,
    route: Route,
    status: TripStatus = TripStatus.IN_PROGRESS,
) -> Trip:
    """Helper to seed a test trip."""
    async with async_session_factory() as session:
        trip = Trip(
            route_id=route.id,
            bus_id=bus.id,
            driver_id=driver.id,
            status=status,
            actual_start_at=datetime.now(timezone.utc) if status == TripStatus.IN_PROGRESS else None,
        )
        session.add(trip)
        await session.commit()
        await session.refresh(trip)
        return trip


def mock_firebase_token(uid: str, email: str):
    return patch(
        "app.core.security.verify_firebase_token",
        return_value={"uid": uid, "email": email},
    )


# --- 1. PARENT REGISTRATION & VALIDATION TESTS ---

@pytest.mark.asyncio
async def test_parent_registration_success(async_client: AsyncClient):
    """Parent can register with a valid student email and create a PENDING request."""
    student = await create_test_user(UserRole.STUDENT, prefix="student")
    parent_uid = f"fb-parent-{uuid.uuid4().hex[:8]}"
    parent_email = f"parent_{uuid.uuid4().hex[:8]}@gmail.com"

    payload = {
        "email": parent_email,
        "full_name": "Parent User",
        "child_email": student.email,
    }

    with mock_firebase_token(parent_uid, parent_email):
        res = await async_client.post(
            "/api/v1/auth/register-parent",
            json=payload,
            headers={"Authorization": "Bearer mock-parent-token"},
        )

    assert res.status_code == 201
    data = res.json()
    assert data["student_id"] == str(student.id)
    assert data["status"] == "PENDING"
    assert data["approved_at"] is None
    assert data["student_email"] == student.email


@pytest.mark.asyncio
async def test_parent_registration_rejects_non_sode_domain(async_client: AsyncClient):
    """Parent registration rejects non-@sode-edu.in child email with 422."""
    parent_uid = f"fb-parent-{uuid.uuid4().hex[:8]}"
    parent_email = f"parent_{uuid.uuid4().hex[:8]}@gmail.com"

    payload = {
        "email": parent_email,
        "full_name": "Parent User",
        "child_email": "invalid_child@gmail.com",
    }

    with mock_firebase_token(parent_uid, parent_email):
        res = await async_client.post(
            "/api/v1/auth/register-parent",
            json=payload,
            headers={"Authorization": "Bearer mock-parent-token"},
        )

    assert res.status_code == 422


@pytest.mark.asyncio
async def test_parent_registration_rejects_nonexistent_student(async_client: AsyncClient):
    """Parent registration rejects non-existent student email with 404."""
    parent_uid = f"fb-parent-{uuid.uuid4().hex[:8]}"
    parent_email = f"parent_{uuid.uuid4().hex[:8]}@gmail.com"

    payload = {
        "email": parent_email,
        "full_name": "Parent User",
        "child_email": "nonexistent_student_9999@sode-edu.in",
    }

    with mock_firebase_token(parent_uid, parent_email):
        res = await async_client.post(
            "/api/v1/auth/register-parent",
            json=payload,
            headers={"Authorization": "Bearer mock-parent-token"},
        )

    assert res.status_code == 404
    assert "Student with specified email not found" in res.json()["detail"]


@pytest.mark.asyncio
async def test_parent_registration_rejects_non_student_role(async_client: AsyncClient):
    """Parent registration rejects referenced email if user is not a STUDENT (e.g. DRIVER/ADMIN)."""
    driver = await create_test_user(UserRole.DRIVER, prefix="driver_not_student")
    # Manually update driver email to sode-edu.in for this test
    async with async_session_factory() as session:
        driver_db = await session.get(User, driver.id)
        driver_db.email = f"driver_{uuid.uuid4().hex[:6]}@sode-edu.in"
        await session.commit()
        driver_email = driver_db.email

    parent_uid = f"fb-parent-{uuid.uuid4().hex[:8]}"
    parent_email = f"parent_{uuid.uuid4().hex[:8]}@gmail.com"

    payload = {
        "email": parent_email,
        "full_name": "Parent User",
        "child_email": driver_email,
    }

    with mock_firebase_token(parent_uid, parent_email):
        res = await async_client.post(
            "/api/v1/auth/register-parent",
            json=payload,
            headers={"Authorization": "Bearer mock-parent-token"},
        )

    assert res.status_code == 400
    assert "Referenced user is not a student" in res.json()["detail"]


@pytest.mark.asyncio
async def test_parent_registration_idempotency(async_client: AsyncClient):
    """Registering with same parent and student when request is PENDING returns the existing request."""
    student = await create_test_user(UserRole.STUDENT)
    parent_uid = f"fb-parent-{uuid.uuid4().hex[:8]}"
    parent_email = f"parent_{uuid.uuid4().hex[:8]}@gmail.com"

    payload = {
        "email": parent_email,
        "full_name": "Parent User",
        "child_email": student.email,
    }

    with mock_firebase_token(parent_uid, parent_email):
        res1 = await async_client.post(
            "/api/v1/auth/register-parent",
            json=payload,
            headers={"Authorization": "Bearer mock-parent-token"},
        )
        res2 = await async_client.post(
            "/api/v1/auth/register-parent",
            json=payload,
            headers={"Authorization": "Bearer mock-parent-token"},
        )

    assert res1.status_code == 201
    assert res2.status_code == 201
    assert res1.json()["id"] == res2.json()["id"]


# --- 2. STUDENT APPROVAL / REJECTION TESTS ---

@pytest.mark.asyncio
async def test_student_can_list_own_pending_requests(async_client: AsyncClient):
    """Student can list parent link requests sent to them."""
    student = await create_test_user(UserRole.STUDENT)
    parent = await create_test_user(UserRole.PARENT)

    async with async_session_factory() as session:
        req = ParentLinkRequest(
            parent_id=parent.id,
            student_id=student.id,
            status=ParentLinkStatus.PENDING,
        )
        session.add(req)
        await session.commit()
        req_id = req.id

    with mock_firebase_token(student.firebase_uid, student.email):
        res = await async_client.get(
            "/api/v1/parent-links",
            headers={"Authorization": "Bearer mock-student-token"},
        )

    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert any(r["id"] == str(req_id) for r in data)


@pytest.mark.asyncio
async def test_student_approval_creates_parent_children(async_client: AsyncClient):
    """Student approves request -> status becomes APPROVED, approved_at populated, ParentChildren created."""
    student = await create_test_user(UserRole.STUDENT)
    parent = await create_test_user(UserRole.PARENT)

    async with async_session_factory() as session:
        req = ParentLinkRequest(
            parent_id=parent.id,
            student_id=student.id,
            status=ParentLinkStatus.PENDING,
        )
        session.add(req)
        await session.commit()
        await session.refresh(req)
        req_id = req.id

    with mock_firebase_token(student.firebase_uid, student.email):
        res = await async_client.post(
            f"/api/v1/parent-links/{req_id}/approve",
            headers={"Authorization": "Bearer mock-student-token"},
        )

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "APPROVED"
    assert data["approved_at"] is not None

    # Verify ParentChildren row in database
    async with async_session_factory() as session:
        pc_link = await session.execute(
            select(ParentChildren).where(
                ParentChildren.parent_id == parent.id,
                ParentChildren.student_id == student.id,
            )
        )
        assert pc_link.scalar_one_or_none() is not None



@pytest.mark.asyncio
async def test_student_cannot_approve_another_students_request(async_client: AsyncClient):
    """Student cannot approve a request addressed to a different student."""
    student1 = await create_test_user(UserRole.STUDENT)
    student2 = await create_test_user(UserRole.STUDENT)
    parent = await create_test_user(UserRole.PARENT)

    async with async_session_factory() as session:
        req = ParentLinkRequest(
            parent_id=parent.id,
            student_id=student1.id,
            status=ParentLinkStatus.PENDING,
        )
        session.add(req)
        await session.commit()
        req_id = req.id

    # Student 2 tries to approve student 1's request -> 403
    with mock_firebase_token(student2.firebase_uid, student2.email):
        res = await async_client.post(
            f"/api/v1/parent-links/{req_id}/approve",
            headers={"Authorization": "Bearer mock-student2-token"},
        )

    assert res.status_code == 403
    assert "Access forbidden" in res.json()["detail"]


@pytest.mark.asyncio
async def test_non_student_roles_cannot_approve_request(async_client: AsyncClient):
    """Parent, Driver, and Admin roles cannot approve link requests."""
    student = await create_test_user(UserRole.STUDENT)
    parent = await create_test_user(UserRole.PARENT)
    admin = await create_test_user(UserRole.ADMIN)
    bus = await create_test_bus()
    driver = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)

    async with async_session_factory() as session:
        req = ParentLinkRequest(
            parent_id=parent.id,
            student_id=student.id,
            status=ParentLinkStatus.PENDING,
        )
        session.add(req)
        await session.commit()
        req_id = req.id

    # Parent -> 403
    with mock_firebase_token(parent.firebase_uid, parent.email):
        res_par = await async_client.post(
            f"/api/v1/parent-links/{req_id}/approve",
            headers={"Authorization": "Bearer mock-parent-token"},
        )
    assert res_par.status_code == 403

    # Driver -> 403
    with mock_firebase_token(driver.firebase_uid, driver.email):
        res_drv = await async_client.post(
            f"/api/v1/parent-links/{req_id}/approve",
            headers={"Authorization": "Bearer mock-driver-token"},
        )
    assert res_drv.status_code == 403

    # Admin -> 403
    with mock_firebase_token(admin.firebase_uid, admin.email):
        res_adm = await async_client.post(
            f"/api/v1/parent-links/{req_id}/approve",
            headers={"Authorization": "Bearer mock-admin-token"},
        )
    assert res_adm.status_code == 403


@pytest.mark.asyncio
async def test_student_rejection_prevents_parent_children(async_client: AsyncClient):
    """Student rejecting request sets status to REJECTED and does NOT create ParentChildren."""
    student = await create_test_user(UserRole.STUDENT)
    parent = await create_test_user(UserRole.PARENT)

    async with async_session_factory() as session:
        req = ParentLinkRequest(
            parent_id=parent.id,
            student_id=student.id,
            status=ParentLinkStatus.PENDING,
        )
        session.add(req)
        await session.commit()
        req_id = req.id

    with mock_firebase_token(student.firebase_uid, student.email):
        res = await async_client.post(
            f"/api/v1/parent-links/{req_id}/reject",
            headers={"Authorization": "Bearer mock-student-token"},
        )

    assert res.status_code == 200
    assert res.json()["status"] == "REJECTED"

    # Confirm ParentChildren is not created
    async with async_session_factory() as session:
        pc_link = await session.execute(
            select(ParentChildren).where(
                ParentChildren.parent_id == parent.id,
                ParentChildren.student_id == student.id,
            )
        )
        assert pc_link.scalar_one_or_none() is None



# --- 3. PARENT CHILDREN & LIVE LOCATION ACCESS TESTS ---

@pytest.mark.asyncio
async def test_parent_can_list_only_approved_children(async_client: AsyncClient):
    """Parent can list approved children only; pending or unlinked students are not returned."""
    parent1 = await create_test_user(UserRole.PARENT)
    parent2 = await create_test_user(UserRole.PARENT)
    student1 = await create_test_user(UserRole.STUDENT)
    student2 = await create_test_user(UserRole.STUDENT)

    async with async_session_factory() as session:
        # Parent 1 approved link with Student 1
        pc1 = ParentChildren(parent_id=parent1.id, student_id=student1.id)
        # Parent 2 approved link with Student 2
        pc2 = ParentChildren(parent_id=parent2.id, student_id=student2.id)
        session.add_all([pc1, pc2])
        await session.commit()

    with mock_firebase_token(parent1.firebase_uid, parent1.email):
        res = await async_client.get(
            "/api/v1/parent/children",
            headers={"Authorization": "Bearer mock-parent1-token"},
        )

    assert res.status_code == 200
    children = res.json()
    assert len(children) == 1
    assert children[0]["student_id"] == str(student1.id)
    assert children[0]["student_email"] == student1.email


@pytest.mark.asyncio
async def test_parent_cannot_access_unapproved_child_live_location(async_client: AsyncClient):
    """Parent cannot access live location of a student without an approved link (403 Forbidden)."""
    parent = await create_test_user(UserRole.PARENT)
    student = await create_test_user(UserRole.STUDENT)

    with mock_firebase_token(parent.firebase_uid, parent.email):
        res = await async_client.get(
            f"/api/v1/parent/children/{student.id}/live",
            headers={"Authorization": "Bearer mock-parent-token"},
        )

    assert res.status_code == 403
    assert "Access forbidden" in res.json()["detail"]


@pytest.mark.asyncio
async def test_parent_access_approved_child_live_location_success(async_client: AsyncClient):
    """Parent can access live location for approved child with an active in-progress trip."""
    bus = await create_test_bus()
    driver = await create_test_user(UserRole.DRIVER, assigned_bus_id=bus.id)
    student = await create_test_user(UserRole.STUDENT, assigned_bus_id=bus.id)
    parent = await create_test_user(UserRole.PARENT)
    route = await create_test_route()
    trip = await create_test_trip(driver, bus, route, TripStatus.IN_PROGRESS)

    # Establish approved parent-child link
    async with async_session_factory() as session:
        pc = ParentChildren(parent_id=parent.id, student_id=student.id)
        session.add(pc)
        await session.commit()

    # Seed live location in Redis
    now = datetime.now(timezone.utc)
    await update_trip_live_location(
        trip_id=trip.id,
        driver_id=driver.id,
        bus_id=bus.id,
        latitude=13.3415,
        longitude=74.7415,
        recorded_at=now,
        received_at=now,
        accuracy_meters=3.0,
        speed_mps=12.5,
        heading_degrees=45.0,
    )

    with mock_firebase_token(parent.firebase_uid, parent.email):
        res = await async_client.get(
            f"/api/v1/parent/children/{student.id}/live",
            headers={"Authorization": "Bearer mock-parent-token"},
        )

    assert res.status_code == 200
    data = res.json()
    assert data["trip_id"] == str(trip.id)
    assert data["bus_id"] == str(bus.id)
    assert data["latitude"] == 13.3415
    assert data["longitude"] == 74.7415
    assert data["speed_mps"] == 12.5


@pytest.mark.asyncio
async def test_parent_access_child_no_active_trip_returns_404(async_client: AsyncClient):
    """Approved child with no active trip returns 404."""
    bus = await create_test_bus()
    student = await create_test_user(UserRole.STUDENT, assigned_bus_id=bus.id)
    parent = await create_test_user(UserRole.PARENT)

    async with async_session_factory() as session:
        pc = ParentChildren(parent_id=parent.id, student_id=student.id)
        session.add(pc)
        await session.commit()

    with mock_firebase_token(parent.firebase_uid, parent.email):
        res = await async_client.get(
            f"/api/v1/parent/children/{student.id}/live",
            headers={"Authorization": "Bearer mock-parent-token"},
        )

    assert res.status_code == 404
    assert "No active in-progress trip found" in res.json()["detail"]
