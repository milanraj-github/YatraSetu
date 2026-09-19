import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional
import uuid

from firebase_admin import messaging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.firebase import initialize_firebase_app
from app.core.redis import get_redis_client
from app.models.device_token import UserDeviceToken
from app.models.enums import DevicePlatform, NotificationChannel, NotificationStatus, NotificationType
from app.models.notification import Notification

logger = logging.getLogger(__name__)


def is_unregistered_token_error(exc: Exception) -> bool:
    """Check if Firebase exception indicates an invalid or unregistered token."""
    if isinstance(exc, messaging.UnregisteredError):
        return True
    exc_str = str(exc).lower()
    if (
        "not registered" in exc_str
        or "unregistered" in exc_str
        or "registration-token-not-registered" in exc_str
    ):
        return True
    return False


async def register_device_token(
    db: AsyncSession,
    user_id: uuid.UUID,
    fcm_token: str,
    platform: DevicePlatform = DevicePlatform.ANDROID,
) -> UserDeviceToken:
    """Register or reactivate an FCM device token for a user idempotently."""
    stmt = select(UserDeviceToken).where(UserDeviceToken.fcm_token == fcm_token)
    result = await db.execute(stmt)
    existing_token = result.scalar_one_or_none()

    if existing_token:
        existing_token.user_id = user_id
        existing_token.platform = platform
        existing_token.is_active = True
        await db.commit()
        await db.refresh(existing_token)
        return existing_token

    new_token = UserDeviceToken(
        user_id=user_id,
        fcm_token=fcm_token,
        platform=platform,
        is_active=True,
    )
    db.add(new_token)
    await db.commit()
    await db.refresh(new_token)
    return new_token


async def deactivate_device_token(
    db: AsyncSession,
    user_id: uuid.UUID,
    device_id: uuid.UUID,
) -> bool:
    """Deactivate a device token belonging to a specific user."""
    stmt = select(UserDeviceToken).where(
        UserDeviceToken.id == device_id,
        UserDeviceToken.user_id == user_id,
    )
    result = await db.execute(stmt)
    token = result.scalar_one_or_none()
    if not token:
        return False

    token.is_active = False
    await db.commit()
    return True


async def check_and_acquire_dedupe_lock(
    recipient_id: uuid.UUID,
    notification_type: NotificationType,
    event_key: str,
    ttl_seconds: int = 1800,
) -> bool:
    """Check and acquire a 30-minute deduplication lock in Redis.

    Returns:
        True if lock was acquired (notification should proceed).
        False if lock already exists (notification is a duplicate).
    """
    try:
        redis_client = get_redis_client()
        lock_key = (
            f"smartbus:notification:dedupe:{recipient_id}:{notification_type.value}:{event_key}"
        )
        acquired = await redis_client.set(lock_key, "1", ex=ttl_seconds, nx=True)
        return bool(acquired)
    except Exception as exc:
        logger.warning(
            f"Redis deduplication lock check failed (allowing delivery): {exc}"
        )
        return True


async def create_notification(
    db: AsyncSession,
    recipient_id: uuid.UUID,
    title: str,
    body: str,
    notification_type: NotificationType,
    channel: NotificationChannel = NotificationChannel.PUSH,
    data_payload: Optional[Dict[str, Any]] = None,
) -> Notification:
    """Persist a new notification record in PENDING state before dispatch."""
    notification = Notification(
        recipient_id=recipient_id,
        title=title,
        body=body,
        notification_type=notification_type,
        channel=channel,
        status=NotificationStatus.PENDING,
        data_payload=data_payload,
    )
    db.add(notification)
    await db.flush()
    await db.refresh(notification)
    return notification


async def send_fcm_push(
    db: AsyncSession,
    recipient_id: uuid.UUID,
    title: str,
    body: str,
    data_payload: Optional[Dict[str, Any]] = None,
) -> tuple[int, int]:
    """Send push notification to all active device tokens of recipient.

    Returns:
        tuple (success_count, failure_count)
    """
    if not settings.FCM_ENABLED:
        logger.info("FCM is disabled in settings; skipping push dispatch")
        return 0, 0

    stmt = select(UserDeviceToken).where(
        UserDeviceToken.user_id == recipient_id,
        UserDeviceToken.is_active.is_(True),
    )
    result = await db.execute(stmt)
    tokens = list(result.scalars().all())

    if not tokens:
        return 0, 0

    app = initialize_firebase_app()
    if app is None:
        logger.warning("Firebase app is not initialized; cannot send FCM messages")
        return 0, len(tokens)

    # Convert all payload values to strings for FCM data payload
    fcm_data: Optional[Dict[str, str]] = None
    if data_payload:
        fcm_data = {str(k): str(v) for k, v in data_payload.items()}

    success_count = 0
    failure_count = 0
    tokens_deactivated = 0

    for device_token in tokens:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=fcm_data,
            token=device_token.fcm_token,
        )
        try:
            # Execute blocking FCM call in worker thread
            await asyncio.to_thread(messaging.send, message, app=app)
            success_count += 1
        except Exception as exc:
            failure_count += 1
            if is_unregistered_token_error(exc):
                logger.info(
                    f"FCM token unregistered/invalid for token id={device_token.id}. Deactivating."
                )
                device_token.is_active = False
                tokens_deactivated += 1
            else:
                logger.warning(
                    f"FCM delivery error for token id={device_token.id}: {exc}"
                )

    if tokens_deactivated > 0:
        await db.commit()

    return success_count, failure_count


async def send_notification(
    db: AsyncSession,
    recipient_id: uuid.UUID,
    title: str,
    body: str,
    notification_type: NotificationType,
    channel: NotificationChannel = NotificationChannel.PUSH,
    data_payload: Optional[Dict[str, Any]] = None,
    event_key: Optional[str] = None,
) -> Optional[Notification]:
    """Persist and dispatch a notification, respecting Redis deduplication."""
    if event_key:
        acquired = await check_and_acquire_dedupe_lock(
            recipient_id=recipient_id,
            notification_type=notification_type,
            event_key=event_key,
            ttl_seconds=settings.NOTIFICATION_DEDUPE_TTL_SECONDS,
        )
        if not acquired:
            logger.info(
                f"Notification suppressed due to deduplication: recipient={recipient_id}, type={notification_type}, event_key={event_key}"
            )
            return None

    # Step 1: Persist notification record with status PENDING
    notif = await create_notification(
        db=db,
        recipient_id=recipient_id,
        title=title,
        body=body,
        notification_type=notification_type,
        channel=channel,
        data_payload=data_payload,
    )

    # Step 2: Dispatch push notification if channel is PUSH or BOTH
    if channel in (NotificationChannel.PUSH, NotificationChannel.BOTH):
        success_count, failure_count = await send_fcm_push(
            db=db,
            recipient_id=recipient_id,
            title=title,
            body=body,
            data_payload=data_payload,
        )
        if success_count > 0:
            notif.status = NotificationStatus.SENT
            notif.sent_at = datetime.now(timezone.utc)
            notif.error_message = None
        elif failure_count > 0:
            notif.status = NotificationStatus.FAILED
            notif.error_message = f"FCM delivery failed for all {failure_count} device token(s)"
        else:
            # No active device tokens
            notif.status = NotificationStatus.PENDING
            notif.error_message = "No active device tokens found for recipient"

    if channel == NotificationChannel.EMAIL:
        notif.status = NotificationStatus.PENDING
        notif.error_message = "Email channel not implemented in current phase"

    await db.commit()
    await db.refresh(notif)
    return notif
