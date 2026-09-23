from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.schemas.auth import APIResponse, UserResponse
from app.models.notification import Notification, NotificationStatus, UserDeviceToken
from app.schemas.notification import NotificationResponse, DeviceTokenRegister

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.post("/device-token", response_model=APIResponse)
async def register_device_token(
    payload: DeviceTokenRegister,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    from app.api.v1.tracking import get_db_user_from_auth
    user = await get_db_user_from_auth(db, current_user)
    
    # Check if token exists
    stmt = select(UserDeviceToken).where(UserDeviceToken.token == payload.token)
    res = await db.execute(stmt)
    token_record = res.scalars().first()
    
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    
    if token_record:
        # Transfer token to new user if changed, or just update last_seen
        token_record.user_id = user.id
        token_record.platform = payload.platform or token_record.platform
        token_record.device_name = payload.device_name or token_record.device_name
        token_record.is_active = True
        token_record.last_seen_at = now_utc
    else:
        new_token = UserDeviceToken(
            user_id=user.id,
            token=payload.token,
            platform=payload.platform,
            device_name=payload.device_name,
            is_active=True,
            last_seen_at=now_utc
        )
        db.add(new_token)
        
    await db.commit()
    return APIResponse(success=True, message="Device token registered.")

@router.get("", response_model=APIResponse[List[NotificationResponse]])
async def get_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
    limit: int = Query(50, le=100)
):
    from app.api.v1.tracking import get_db_user_from_auth
    user = await get_db_user_from_auth(db, current_user)
    
    stmt = select(Notification).where(Notification.user_id == user.id).order_by(desc(Notification.created_at)).limit(limit)
    res = await db.execute(stmt)
    notifications = res.scalars().all()
    
    return APIResponse(success=True, data=[NotificationResponse.model_validate(n) for n in notifications])

@router.get("/unread-count", response_model=APIResponse)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    from app.api.v1.tracking import get_db_user_from_auth
    user = await get_db_user_from_auth(db, current_user)
    
    stmt = select(func.count(Notification.id)).where(
        Notification.user_id == user.id,
        Notification.status != NotificationStatus.READ
    )
    res = await db.execute(stmt)
    count = res.scalar()
    
    return APIResponse(success=True, data={"unread_count": count})

@router.post("/{notification_id}/read", response_model=APIResponse)
async def mark_notification_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    from app.api.v1.tracking import get_db_user_from_auth
    user = await get_db_user_from_auth(db, current_user)
    
    stmt = select(Notification).where(Notification.id == notification_id, Notification.user_id == user.id)
    res = await db.execute(stmt)
    notification = res.scalars().first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    if notification.status != NotificationStatus.READ:
        notification.status = NotificationStatus.READ
        notification.read_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()
        
    return APIResponse(success=True, message="Marked as read")

@router.delete("/device-token", response_model=APIResponse)
async def delete_device_token(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    from app.api.v1.tracking import get_db_user_from_auth
    user = await get_db_user_from_auth(db, current_user)
    
    stmt = select(UserDeviceToken).where(UserDeviceToken.token == token, UserDeviceToken.user_id == user.id)
    res = await db.execute(stmt)
    token_record = res.scalars().first()
    
    if token_record:
        token_record.is_active = False
        await db.commit()
        
    return APIResponse(success=True, message="Device token deactivated.")
