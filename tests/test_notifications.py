import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest
from firebase_admin import messaging
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.db.database import async_session_factory
from app.models.device_token import UserDeviceToken
from app.models.enums import (
    DevicePlatform,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
    UserRole,
)
from app.models.notification import Notification
from app.models.user import User
from app.services import notification_service


async def create_test_user(
    role: UserRole = UserRole.STUDENT,
    prefix: str = "notif_user",
) -> User:
    """Helper to seed a test user with a specific role."""
    test_uid = f"fb-notif-{role.value.lower()}-{uuid.uuid4().hex[:8]}"
    domain = "sode-edu.in" if role == UserRole.STUDENT else "example.com"
    test_email = f"{prefix}_{uuid.uuid4().hex[:8]}@{domain}"

    async with async_session_factory() as session:
        user = User(
            firebase_uid=test_uid,
            email=test_email,
            full_name=f"Notif Test {role.value}",
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


def mock_firebase_token(uid: str, email: str):
    return patch(
        "app.core.security.verify_firebase_token",
        return_value={"uid": uid, "email": email},
    )


# --- 1. DEVICE TOKEN REGISTRATION & DEACTIVATION API TESTS ---

@pytest.mark.asyncio
async def test_register_device_token_unauthenticated(async_client: AsyncClient):
    """Accessing device token registration without Bearer token must return 401."""
    res = await async_client.post(
        "/api/v1/notifications/devices",
        json={"fcm_token": "fcm-fake-token-123", "platform": "ANDROID"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_register_device_token_success(async_client: AsyncClient):
    """Authenticated user can register a device token without leaking raw token in response."""
    user = await create_test_user(UserRole.PARENT, prefix="parent")
    fcm_token_val = f"fcm-sample-token-{uuid.uuid4().hex}"

    with mock_firebase_token(user.firebase_uid, user.email):
        res = await async_client.post(
            "/api/v1/notifications/devices",
            json={"fcm_token": fcm_token_val, "platform": "ANDROID"},
            headers={"Authorization": "Bearer mock-token"},
        )

    assert res.status_code == 200
    data = res.json()
    assert "id" in data
    assert data["platform"] == "ANDROID"
    assert data["is_active"] is True
    assert "created_at" in data
    # Verify raw token is NOT in response payload
    assert "fcm_token" not in data

    # Verify database persistence
    async with async_session_factory() as session:
        stmt = select(UserDeviceToken).where(UserDeviceToken.id == uuid.UUID(data["id"]))
        result = await session.execute(stmt)
        token_row = result.scalar_one_or_none()
        assert token_row is not None
        assert token_row.user_id == user.id
        assert token_row.fcm_token == fcm_token_val
        assert token_row.is_active is True


@pytest.mark.asyncio
async def test_register_device_token_idempotency_and_reactivation(async_client: AsyncClient):
    """Re-registering existing or inactive token reactivates it idempotently."""
    user = await create_test_user(UserRole.STUDENT, prefix="student")
    fcm_token_val = f"fcm-reused-{uuid.uuid4().hex}"

    # First registration
    with mock_firebase_token(user.firebase_uid, user.email):
        res1 = await async_client.post(
            "/api/v1/notifications/devices",
            json={"fcm_token": fcm_token_val, "platform": "ANDROID"},
            headers={"Authorization": "Bearer mock-token"},
        )
    assert res1.status_code == 200
    token_id = res1.json()["id"]

    # Deactivate the token in DB
    async with async_session_factory() as session:
        stmt = select(UserDeviceToken).where(UserDeviceToken.id == uuid.UUID(token_id))
        result = await session.execute(stmt)
        token_row = result.scalar_one()
        token_row.is_active = False
        await session.commit()

    # Re-register with platform IOS
    with mock_firebase_token(user.firebase_uid, user.email):
        res2 = await async_client.post(
            "/api/v1/notifications/devices",
            json={"fcm_token": fcm_token_val, "platform": "IOS"},
            headers={"Authorization": "Bearer mock-token"},
        )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["id"] == token_id
    assert data2["platform"] == "IOS"
    assert data2["is_active"] is True

    # Check that there is still only 1 row for this token
    async with async_session_factory() as session:
        stmt = select(UserDeviceToken).where(UserDeviceToken.fcm_token == fcm_token_val)
        result = await session.execute(stmt)
        rows = list(result.scalars().all())
        assert len(rows) == 1
        assert rows[0].is_active is True
        assert rows[0].platform == DevicePlatform.IOS


@pytest.mark.asyncio
async def test_deactivate_device_token_success(async_client: AsyncClient):
    """User can deactivate their own registered device token."""
    user = await create_test_user(UserRole.DRIVER, prefix="driver")
    fcm_token_val = f"fcm-deact-{uuid.uuid4().hex}"

    async with async_session_factory() as session:
        token = UserDeviceToken(
            user_id=user.id,
            fcm_token=fcm_token_val,
            platform=DevicePlatform.ANDROID,
            is_active=True,
        )
        session.add(token)
        await session.commit()
        await session.refresh(token)
        token_id = token.id

    with mock_firebase_token(user.firebase_uid, user.email):
        res = await async_client.delete(
            f"/api/v1/notifications/devices/{token_id}",
            headers={"Authorization": "Bearer mock-token"},
        )
    assert res.status_code == 204

    # Verify in DB that is_active is False
    async with async_session_factory() as session:
        stmt = select(UserDeviceToken).where(UserDeviceToken.id == token_id)
        result = await session.execute(stmt)
        token_row = result.scalar_one()
        assert token_row.is_active is False


@pytest.mark.asyncio
async def test_deactivate_device_token_unauthorized_or_not_found(async_client: AsyncClient):
    """Attempting to deactivate another user's or non-existent token returns 404."""
    user_a = await create_test_user(UserRole.STUDENT, prefix="user_a")
    user_b = await create_test_user(UserRole.STUDENT, prefix="user_b")

    fcm_token_val = f"fcm-a-{uuid.uuid4().hex}"
    async with async_session_factory() as session:
        token_a = UserDeviceToken(
            user_id=user_a.id,
            fcm_token=fcm_token_val,
            platform=DevicePlatform.ANDROID,
            is_active=True,
        )
        session.add(token_a)
        await session.commit()
        await session.refresh(token_a)
        token_a_id = token_a.id

    # User B tries to delete User A's token
    with mock_firebase_token(user_b.firebase_uid, user_b.email):
        res = await async_client.delete(
            f"/api/v1/notifications/devices/{token_a_id}",
            headers={"Authorization": "Bearer mock-token"},
        )
    assert res.status_code == 404

    # Non-existent token ID
    with mock_firebase_token(user_a.firebase_uid, user_a.email):
        res_nonexistent = await async_client.delete(
            f"/api/v1/notifications/devices/{uuid.uuid4()}",
            headers={"Authorization": "Bearer mock-token"},
        )
    assert res_nonexistent.status_code == 404


# --- 2. NOTIFICATION PERSISTENCE & DISPATCH SERVICE TESTS ---

@pytest.mark.asyncio
async def test_create_notification_persistence():
    """create_notification accurately persists notification in PENDING status."""
    user = await create_test_user(UserRole.STUDENT, prefix="student_notif")

    async with async_session_factory() as session:
        notif = await notification_service.create_notification(
            db=session,
            recipient_id=user.id,
            title="Bus Approaching",
            body="Bus KA-20-1234 is 2 stops away.",
            notification_type=NotificationType.BUS_NEARBY,
            channel=NotificationChannel.PUSH,
            data_payload={"stop_id": "123", "eta_minutes": 5},
        )
        await session.commit()
        notif_id = notif.id

    async with async_session_factory() as session:
        stmt = select(Notification).where(Notification.id == notif_id)
        result = await session.execute(stmt)
        stored = result.scalar_one()
        assert stored.recipient_id == user.id
        assert stored.title == "Bus Approaching"
        assert stored.notification_type == NotificationType.BUS_NEARBY
        assert stored.status == NotificationStatus.PENDING
        assert stored.data_payload == {"stop_id": "123", "eta_minutes": 5}


@pytest.mark.asyncio
async def test_send_fcm_push_success():
    """send_fcm_push dispatches push notification to all active tokens and returns counts."""
    user = await create_test_user(UserRole.PARENT, prefix="parent_push")

    async with async_session_factory() as session:
        t1 = UserDeviceToken(
            user_id=user.id,
            fcm_token=f"token-1-{uuid.uuid4().hex}",
            platform=DevicePlatform.ANDROID,
            is_active=True,
        )
        t2 = UserDeviceToken(
            user_id=user.id,
            fcm_token=f"token-2-{uuid.uuid4().hex}",
            platform=DevicePlatform.IOS,
            is_active=True,
        )
        session.add_all([t1, t2])
        await session.commit()

    with patch("firebase_admin.messaging.send", return_value="projects/test/messages/msg-123") as mock_send, \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        async with async_session_factory() as session:
            success, failure = await notification_service.send_fcm_push(
                db=session,
                recipient_id=user.id,
                title="Bus Arrived",
                body="Bus has arrived at your boarding stop.",
                data_payload={"route_id": "rt-1"},
            )

    assert success == 2
    assert failure == 0
    assert mock_send.call_count == 2


@pytest.mark.asyncio
async def test_send_fcm_push_token_invalidation():
    """UnregisteredError deactivates the invalid token in the database."""
    user = await create_test_user(UserRole.STUDENT, prefix="student_inval")

    async with async_session_factory() as session:
        token_stale = UserDeviceToken(
            user_id=user.id,
            fcm_token=f"token-stale-{uuid.uuid4().hex}",
            platform=DevicePlatform.ANDROID,
            is_active=True,
        )
        token_good = UserDeviceToken(
            user_id=user.id,
            fcm_token=f"token-good-{uuid.uuid4().hex}",
            platform=DevicePlatform.ANDROID,
            is_active=True,
        )
        session.add_all([token_stale, token_good])
        await session.commit()
        stale_id = token_stale.id
        good_id = token_good.id

    def fake_send(message, app=None):
        if "token-stale" in message.token:
            raise messaging.UnregisteredError("Requested entity was not found")
        return "projects/test/messages/msg-good"

    with patch("firebase_admin.messaging.send", side_effect=fake_send), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        async with async_session_factory() as session:
            success, failure = await notification_service.send_fcm_push(
                db=session,
                recipient_id=user.id,
                title="Delay Alert",
                body="Trip delayed by 15 mins due to traffic.",
            )

    assert success == 1
    assert failure == 1

    # Verify in DB: stale token is deactivated, good token remains active
    async with async_session_factory() as session:
        stale_row = (await session.execute(select(UserDeviceToken).where(UserDeviceToken.id == stale_id))).scalar_one()
        good_row = (await session.execute(select(UserDeviceToken).where(UserDeviceToken.id == good_id))).scalar_one()
        assert stale_row.is_active is False
        assert good_row.is_active is True


@pytest.mark.asyncio
async def test_send_notification_no_active_tokens():
    """send_notification marks status as PENDING if recipient has no active device tokens."""
    user = await create_test_user(UserRole.PARENT, prefix="parent_notok")

    async with async_session_factory() as session:
        notif = await notification_service.send_notification(
            db=session,
            recipient_id=user.id,
            title="Update",
            body="Bus has departed.",
            notification_type=NotificationType.BUS_NEARBY,
            channel=NotificationChannel.PUSH,
        )

    assert notif is not None
    assert notif.status == NotificationStatus.PENDING
    assert "No active device tokens" in (notif.error_message or "")


@pytest.mark.asyncio
async def test_send_notification_full_flow_success():
    """send_notification records SENT status and sent_at timestamp when push succeeds."""
    user = await create_test_user(UserRole.STUDENT, prefix="student_full")

    async with async_session_factory() as session:
        t = UserDeviceToken(
            user_id=user.id,
            fcm_token=f"token-ok-{uuid.uuid4().hex}",
            platform=DevicePlatform.ANDROID,
            is_active=True,
        )
        session.add(t)
        await session.commit()

    with patch("firebase_admin.messaging.send", return_value="projects/test/messages/msg-ok"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        async with async_session_factory() as session:
            notif = await notification_service.send_notification(
                db=session,
                recipient_id=user.id,
                title="Bus Nearby",
                body="Your bus is approaching your stop.",
                notification_type=NotificationType.BUS_NEARBY,
                channel=NotificationChannel.PUSH,
                event_key=f"trip-{uuid.uuid4().hex[:6]}",
            )

    assert notif is not None
    assert notif.status == NotificationStatus.SENT
    assert notif.sent_at is not None
    assert notif.error_message is None


# --- 3. REDIS DEDUPLICATION TESTS ---

@pytest.mark.asyncio
async def test_redis_notification_deduplication():
    """Repeated notifications with the same recipient, type, and event_key are deduplicated."""
    user = await create_test_user(UserRole.STUDENT, prefix="student_dedupe")
    event_key = f"trip-event-{uuid.uuid4().hex[:8]}"

    with patch("firebase_admin.messaging.send", return_value="projects/test/messages/msg-dedupe"), \
         patch("app.services.notification_service.initialize_firebase_app", return_value=MagicMock()):
        # First call: must succeed
        async with async_session_factory() as session:
            notif1 = await notification_service.send_notification(
                db=session,
                recipient_id=user.id,
                title="Bus Nearby",
                body="Bus approaching stop.",
                notification_type=NotificationType.BUS_NEARBY,
                event_key=event_key,
            )
        assert notif1 is not None

        # Second call with same event_key within TTL: must be deduplicated (returns None)
        async with async_session_factory() as session:
            notif2 = await notification_service.send_notification(
                db=session,
                recipient_id=user.id,
                title="Bus Nearby",
                body="Bus approaching stop.",
                notification_type=NotificationType.BUS_NEARBY,
                event_key=event_key,
            )
        assert notif2 is None

        # Call with different event_key: must succeed
        different_event_key = f"trip-event-other-{uuid.uuid4().hex[:8]}"
        async with async_session_factory() as session:
            notif3 = await notification_service.send_notification(
                db=session,
                recipient_id=user.id,
                title="Bus Nearby",
                body="Bus approaching stop.",
                notification_type=NotificationType.BUS_NEARBY,
                event_key=different_event_key,
            )
        assert notif3 is not None


@pytest.mark.asyncio
async def test_redis_deduplication_graceful_degradation():
    """When Redis is unavailable, check_and_acquire_dedupe_lock falls back to True."""
    user_id = uuid.uuid4()
    with patch("app.services.notification_service.get_redis_client", side_effect=RuntimeError("Redis connection lost")):
        acquired = await notification_service.check_and_acquire_dedupe_lock(
            recipient_id=user_id,
            notification_type=NotificationType.BUS_NEARBY,
            event_key="fallback-test-key",
        )
    # Safe policy: allow notification to proceed if dedupe store is down
    assert acquired is True
