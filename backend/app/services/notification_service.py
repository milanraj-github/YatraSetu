import logging
from typing import List, Optional
import datetime as dt
from datetime import timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.sql import func

from app.models.notification import Notification, NotificationPriority, NotificationStatus, UserDeviceToken
from app.models.user import User

logger = logging.getLogger("smartbus.notification")

class EmailProvider:
    @staticmethod
    async def send_email(to_email: str, subject: str, body: str) -> bool:
        # Abstraction for sending email. 
        # In a real environment, read SMTP credentials from os.environ and use aiosmtplib.
        logger.info(f"[EMAIL MOCK] To: {to_email} | Subject: {subject} | Body: {body}")
        return True

async def send_fcm_notification(tokens: List[str], title: str, body: str, data: dict = None) -> List[str]:
    """Sends FCM push notifications and returns a list of tokens that failed/expired."""
    import firebase_admin
    from firebase_admin import messaging
    
    if not firebase_admin._apps:
        logger.warning("Firebase Admin not initialized, skipping real FCM.")
        return []
        
    invalid_tokens = []
    
    # We send multicast
    if not tokens:
        return []
        
    try:
        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
            tokens=tokens
        )
        response = messaging.send_each_for_multicast(message)
        
        for idx, resp in enumerate(response.responses):
            if not resp.success:
                logger.warning(f"FCM failed for token {tokens[idx]}: {resp.exception}")
                # Check if it's an unregistered token (meaning uninstalled or token expired)
                if resp.exception and resp.exception.code in ['messaging/invalid-registration-token', 'messaging/registration-token-not-registered']:
                    invalid_tokens.append(tokens[idx])
    except Exception as e:
        logger.error(f"FCM Error: {e}")
        
    return invalid_tokens

async def dispatch_notification(
    db: AsyncSession,
    user_id: int,
    event_type: str,
    title: str,
    message: str,
    priority: NotificationPriority = NotificationPriority.NORMAL,
    related_entity_id: Optional[int] = None,
    send_email: bool = False
):
    """
    Centralized method to dispatch notifications via DB (In-App), FCM, and Email.
    """
    now_utc = dt.datetime.now(timezone.utc).replace(tzinfo=None)
    
    # 1. Create DB Notification Record
    notification = Notification(
        user_id=user_id,
        event_type=event_type,
        related_entity_id=related_entity_id,
        title=title,
        message=message,
        priority=priority,
        status=NotificationStatus.PENDING
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    
    # 2. Fetch User and Active Devices
    res_user = await db.execute(select(User).where(User.id == user_id))
    user = res_user.scalars().first()
    if not user:
        return
        
    res_tokens = await db.execute(
        select(UserDeviceToken)
        .where(UserDeviceToken.user_id == user_id, UserDeviceToken.is_active == True)
    )
    devices = res_tokens.scalars().all()
    
    # 3. FCM Push
    if devices:
        tokens = [d.token for d in devices]
        data_payload = {
            "type": event_type,
            "notification_id": str(notification.id)
        }
        if related_entity_id:
            data_payload["related_entity_id"] = str(related_entity_id)
            
        invalid_tokens = await send_fcm_notification(tokens, title, message, data=data_payload)
        
        # Deactivate invalid tokens
        if invalid_tokens:
            for d in devices:
                if d.token in invalid_tokens:
                    d.is_active = False
            await db.commit()
            
    # 4. Email Fallback (only for High/Critical usually, or if explicitly requested)
    if send_email and user.email:
        email_success = await EmailProvider.send_email(user.email, title, message)
        if not email_success:
            logger.warning(f"Email failed to {user.email}")
            
    # Update Status
    notification.status = NotificationStatus.SENT
    notification.sent_at = now_utc
    await db.commit()

async def notify_admins(
    db: AsyncSession,
    event_type: str,
    title: str,
    message: str,
    priority: NotificationPriority = NotificationPriority.NORMAL,
    related_entity_id: Optional[int] = None,
    send_email: bool = False
):
    from app.models.user import UserRole, UserStatus
    # Find all admins
    res = await db.execute(select(User).where(User.role == UserRole.ADMIN, User.status == UserStatus.ACTIVE))
    admins = res.scalars().all()
    for admin in admins:
        await dispatch_notification(
            db=db,
            user_id=admin.id,
            event_type=event_type,
            title=title,
            message=message,
            priority=priority,
            related_entity_id=related_entity_id,
            send_email=send_email
        )

async def notify_students(
    db: AsyncSession,
    bus_id: int,
    event_type: str,
    title: str,
    message: str,
    priority: NotificationPriority = NotificationPriority.NORMAL,
    related_entity_id: Optional[int] = None,
    send_email: bool = False
):
    from app.models.student_assignment import StudentBusAssignment, StudentAssignmentStatus
    from app.models.parent_student_relationship import ParentStudentRelationship, RelationshipStatus
    
    stmt = select(StudentBusAssignment.student_id).where(
        StudentBusAssignment.bus_id == bus_id,
        StudentBusAssignment.status == StudentAssignmentStatus.ACTIVE
    )
    res = await db.execute(stmt)
    student_ids = res.scalars().all()
    
    recipients = set(student_ids)
    
    if student_ids:
        # Also notify Parents of these students
        parent_stmt = select(ParentStudentRelationship.parent_id).where(
            ParentStudentRelationship.student_id.in_(student_ids),
            ParentStudentRelationship.status == RelationshipStatus.ACTIVE
        )
        parent_res = await db.execute(parent_stmt)
        parent_ids = parent_res.scalars().all()
        recipients.update(parent_ids)
    
    for user_id in recipients:
        await dispatch_notification(
            db=db,
            user_id=user_id,
            event_type=event_type,
            title=title,
            message=message,
            priority=priority,
            related_entity_id=related_entity_id,
            send_email=send_email
        )
