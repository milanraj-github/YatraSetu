import uuid
from unittest.mock import patch
import pytest
from httpx import AsyncClient

from app.db.database import async_session_factory
from app.models.boarding_point import BoardingPoint
from app.models.enums import UserRole
from app.models.route import Route
from app.models.route_stop import RouteStop
from app.models.user import User


async def create_test_user(role: UserRole, prefix: str = "user") -> User:
    """Helper to seed a test user."""
    test_uid = f"fb-rs-{role.value.lower()}-{uuid.uuid4().hex[:8]}"
    domain = "sode-edu.in" if role == UserRole.STUDENT else "test.invalid"
    test_email = f"{prefix}_{uuid.uuid4().hex[:8]}@{domain}"

    async with async_session_factory() as session:
        user = User(
            firebase_uid=test_uid,
            email=test_email,
            full_name=f"RS Test {role.value}",
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def seed_route_and_boarding_points():
    """Helper to seed an active route and two active boarding points."""
    async with async_session_factory() as session:
        route = Route(name="Loop Route", code=f"LP-{uuid.uuid4().hex[:6].upper()}", is_active=True)
        bp1 = BoardingPoint(name="Point 1", latitude=13.3400, longitude=74.7400, is_active=True)
        bp2 = BoardingPoint(name="Point 2", latitude=13.3410, longitude=74.7410, is_active=True)
        bp3 = BoardingPoint(name="Point 3", latitude=13.3420, longitude=74.7420, is_active=True)
        session.add_all([route, bp1, bp2, bp3])
        await session.commit()
        await session.refresh(route)
        await session.refresh(bp1)
        await session.refresh(bp2)
        await session.refresh(bp3)
        return route, bp1, bp2, bp3


# --- ROUTE STOPS TESTS ---

@pytest.mark.asyncio
async def test_add_stop_to_route_success(async_client: AsyncClient):
    """ADMIN can add a boarding point stop to an active route (201 Created)."""
    admin = await create_test_user(UserRole.ADMIN, "admin_rs_add")
    route, bp1, _, _ = await seed_route_and_boarding_points()

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": admin.firebase_uid, "email": admin.email}
        response = await async_client.post(
            f"/api/v1/routes/{route.id}/stops",
            json={
                "boarding_point_id": str(bp1.id),
                "stop_order": 1,
                "scheduled_arrival_offset_minutes": 5,
            },
            headers={"Authorization": "Bearer admin-token"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["route_id"] == str(route.id)
        assert data["boarding_point_id"] == str(bp1.id)
        assert data["stop_order"] == 1
        assert data["scheduled_arrival_offset_minutes"] == 5
        assert data["boarding_point"]["name"] == "Point 1"


@pytest.mark.asyncio
async def test_add_stop_nonexistent_entities_rejected(async_client: AsyncClient):
    """Adding stop with non-existent route or boarding point returns 404."""
    admin = await create_test_user(UserRole.ADMIN, "admin_rs_404")
    route, bp1, _, _ = await seed_route_and_boarding_points()

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": admin.firebase_uid, "email": admin.email}

        # Non-existent route
        r1 = await async_client.post(
            f"/api/v1/routes/{uuid.uuid4()}/stops",
            json={"boarding_point_id": str(bp1.id), "stop_order": 1},
            headers={"Authorization": "Bearer admin-token"},
        )
        assert r1.status_code == 404

        # Non-existent boarding point
        r2 = await async_client.post(
            f"/api/v1/routes/{route.id}/stops",
            json={"boarding_point_id": str(uuid.uuid4()), "stop_order": 1},
            headers={"Authorization": "Bearer admin-token"},
        )
        assert r2.status_code == 404


@pytest.mark.asyncio
async def test_add_stop_inactive_route_or_bp_rejected(async_client: AsyncClient):
    """Adding stop to inactive route or with inactive boarding point returns 400 Bad Request."""
    admin = await create_test_user(UserRole.ADMIN, "admin_rs_inactive")

    async with async_session_factory() as session:
        inactive_route = Route(name="Inactive R", code=f"IR-{uuid.uuid4().hex[:6].upper()}", is_active=False)
        active_route = Route(name="Active R", code=f"AR-{uuid.uuid4().hex[:6].upper()}", is_active=True)
        active_bp = BoardingPoint(name="Active BP", latitude=13.0, longitude=74.0, is_active=True)
        inactive_bp = BoardingPoint(name="Inactive BP", latitude=13.0, longitude=74.0, is_active=False)
        session.add_all([inactive_route, active_route, active_bp, inactive_bp])
        await session.commit()
        await session.refresh(inactive_route)
        await session.refresh(active_route)
        await session.refresh(active_bp)
        await session.refresh(inactive_bp)

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": admin.firebase_uid, "email": admin.email}

        # Inactive route
        r1 = await async_client.post(
            f"/api/v1/routes/{inactive_route.id}/stops",
            json={"boarding_point_id": str(active_bp.id), "stop_order": 1},
            headers={"Authorization": "Bearer admin-token"},
        )
        assert r1.status_code == 400
        assert "inactive route" in r1.json()["detail"]

        # Inactive boarding point
        r2 = await async_client.post(
            f"/api/v1/routes/{active_route.id}/stops",
            json={"boarding_point_id": str(inactive_bp.id), "stop_order": 1},
            headers={"Authorization": "Bearer admin-token"},
        )
        assert r2.status_code == 400
        assert "inactive boarding point" in r2.json()["detail"]


@pytest.mark.asyncio
async def test_add_stop_duplicate_order_or_bp_rejected(async_client: AsyncClient):
    """Duplicate stop_order or duplicate boarding point on same route returns 409 Conflict."""
    admin = await create_test_user(UserRole.ADMIN, "admin_rs_conflict")
    route, bp1, bp2, _ = await seed_route_and_boarding_points()

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": admin.firebase_uid, "email": admin.email}

        # First stop
        r1 = await async_client.post(
            f"/api/v1/routes/{route.id}/stops",
            json={"boarding_point_id": str(bp1.id), "stop_order": 1},
            headers={"Authorization": "Bearer admin-token"},
        )
        assert r1.status_code == 201

        # Duplicate order (order 1 with bp2)
        r2 = await async_client.post(
            f"/api/v1/routes/{route.id}/stops",
            json={"boarding_point_id": str(bp2.id), "stop_order": 1},
            headers={"Authorization": "Bearer admin-token"},
        )
        assert r2.status_code == 409
        assert "Stop order 1 is already taken" in r2.json()["detail"]

        # Duplicate BP (bp1 with order 2)
        r3 = await async_client.post(
            f"/api/v1/routes/{route.id}/stops",
            json={"boarding_point_id": str(bp1.id), "stop_order": 2},
            headers={"Authorization": "Bearer admin-token"},
        )
        assert r3.status_code == 409
        assert "Boarding point is already configured" in r3.json()["detail"]


@pytest.mark.asyncio
async def test_list_update_delete_route_stops(async_client: AsyncClient):
    """ADMIN can list, update, and remove route stops."""
    admin = await create_test_user(UserRole.ADMIN, "admin_rs_crud")
    route, bp1, bp2, _ = await seed_route_and_boarding_points()

    async with async_session_factory() as session:
        rs1 = RouteStop(route_id=route.id, boarding_point_id=bp1.id, stop_order=1, scheduled_arrival_offset_minutes=0)
        rs2 = RouteStop(route_id=route.id, boarding_point_id=bp2.id, stop_order=2, scheduled_arrival_offset_minutes=10)
        session.add_all([rs1, rs2])
        await session.commit()
        await session.refresh(rs1)
        await session.refresh(rs2)
        rs1_id = str(rs1.id)
        rs2_id = str(rs2.id)

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": admin.firebase_uid, "email": admin.email}

        # List stops
        r_list = await async_client.get(f"/api/v1/routes/{route.id}/stops", headers={"Authorization": "Bearer admin-token"})
        assert r_list.status_code == 200
        assert len(r_list.json()) == 2

        # Update stop 1 offset
        r_patch = await async_client.patch(
            f"/api/v1/routes/{route.id}/stops/{rs1_id}",
            json={"scheduled_arrival_offset_minutes": 3},
            headers={"Authorization": "Bearer admin-token"},
        )
        assert r_patch.status_code == 200
        assert r_patch.json()["scheduled_arrival_offset_minutes"] == 3

        # Delete stop 1
        r_del = await async_client.delete(
            f"/api/v1/routes/{route.id}/stops/{rs1_id}",
            headers={"Authorization": "Bearer admin-token"},
        )
        assert r_del.status_code == 204

        # Verify stop 2 was recompacted to order 1
        r_list_after = await async_client.get(f"/api/v1/routes/{route.id}/stops", headers={"Authorization": "Bearer admin-token"})
        assert len(r_list_after.json()) == 1
        assert r_list_after.json()[0]["id"] == rs2_id
        assert r_list_after.json()[0]["stop_order"] == 1


# --- REORDERING TESTS ---

@pytest.mark.asyncio
async def test_reorder_route_stops_3_to_1(async_client: AsyncClient):
    """Test reordering 3 stops: Move stop 3 to order 1.
    Initial: 1=bp1, 2=bp2, 3=bp3
    Expected After Move(3 -> 1): 1=bp3, 2=bp1, 3=bp2
    """
    admin = await create_test_user(UserRole.ADMIN, "admin_reorder")
    route, bp1, bp2, bp3 = await seed_route_and_boarding_points()

    async with async_session_factory() as session:
        rs1 = RouteStop(route_id=route.id, boarding_point_id=bp1.id, stop_order=1)
        rs2 = RouteStop(route_id=route.id, boarding_point_id=bp2.id, stop_order=2)
        rs3 = RouteStop(route_id=route.id, boarding_point_id=bp3.id, stop_order=3)
        session.add_all([rs1, rs2, rs3])
        await session.commit()
        await session.refresh(rs1)
        await session.refresh(rs2)
        await session.refresh(rs3)
        rs1_id, rs2_id, rs3_id = str(rs1.id), str(rs2.id), str(rs3.id)

    with patch("app.core.security.verify_firebase_token") as mock_verify:
        mock_verify.return_value = {"uid": admin.firebase_uid, "email": admin.email}

        # Move stop 3 -> position 1
        response = await async_client.patch(
            f"/api/v1/routes/{route.id}/stops/{rs3_id}/order",
            json={"new_stop_order": 1},
            headers={"Authorization": "Bearer admin-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

        # Verify ordering:
        # Order 1 -> former stop 3 (bp3)
        # Order 2 -> former stop 1 (bp1)
        # Order 3 -> former stop 2 (bp2)
        assert data[0]["id"] == rs3_id
        assert data[0]["stop_order"] == 1
        assert data[0]["boarding_point_id"] == str(bp3.id)

        assert data[1]["id"] == rs1_id
        assert data[1]["stop_order"] == 2
        assert data[1]["boarding_point_id"] == str(bp1.id)

        assert data[2]["id"] == rs2_id
        assert data[2]["stop_order"] == 3
        assert data[2]["boarding_point_id"] == str(bp2.id)

        # Move stop 2 (which is now rs1) to position 3
        r_move2 = await async_client.patch(
            f"/api/v1/routes/{route.id}/stops/{rs1_id}/order",
            json={"new_stop_order": 3},
            headers={"Authorization": "Bearer admin-token"},
        )
        assert r_move2.status_code == 200
        data2 = r_move2.json()
        assert data2[0]["id"] == rs3_id
        assert data2[0]["stop_order"] == 1
        assert data2[1]["id"] == rs2_id
        assert data2[1]["stop_order"] == 2
        assert data2[2]["id"] == rs1_id
        assert data2[2]["stop_order"] == 3
