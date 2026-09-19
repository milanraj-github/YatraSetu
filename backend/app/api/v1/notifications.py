import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.notification import DeviceTokenRegisterRequest, DeviceTokenResponse
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post(
    "/devices",
    response_model=DeviceTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Register or Update Device FCM Push Token",
    description="Register or reactivate an FCM push notification token for the current user.",
)
async def register_device_token_endpoint(
    payload: DeviceTokenRegisterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeviceTokenResponse:
    """Register or update device token for push notifications."""
    token = await notification_service.register_device_token(
        db=db,
        user_id=current_user.id,
        fcm_token=payload.fcm_token,
        platform=payload.platform,
    )
    return DeviceTokenResponse.model_validate(token)


@router.delete(
    "/devices/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate Device Push Token",
    description="Deactivate a registered device push token for the current user.",
)
async def deactivate_device_token_endpoint(
    device_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Deactivate a registered device token."""
    success = await notification_service.deactivate_device_token(
        db=db,
        user_id=current_user.id,
        device_id=device_id,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device token not found or unauthorized",
        )
