from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DevicePlatform, NotificationChannel, NotificationStatus, NotificationType


class DeviceTokenRegisterRequest(BaseModel):
    """Schema for registering or updating a client device FCM token."""

    fcm_token: str = Field(..., min_length=1, max_length=512, description="FCM device push registration token")
    platform: DevicePlatform = Field(
        default=DevicePlatform.ANDROID,
        description="Client device platform (ANDROID, IOS, WEB)",
    )


class DeviceTokenResponse(BaseModel):
    """Schema for device token response without disclosing the full token value."""

    id: uuid.UUID
    platform: DevicePlatform
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationResponse(BaseModel):
    """Schema for notification response representation."""

    id: uuid.UUID
    recipient_id: uuid.UUID
    title: str
    body: str
    notification_type: NotificationType
    channel: NotificationChannel
    status: NotificationStatus
    data_payload: Optional[Dict[str, Any]] = None
    sent_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
